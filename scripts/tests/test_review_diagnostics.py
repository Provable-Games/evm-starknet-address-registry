import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review_runtime as runtime
import review_gate as gate


class ReviewDiagnosticsTests(unittest.TestCase):
    def test_claude_failure_emits_only_allowed_terminal_scalars(self):
        for subtype in runtime.CLAUDE_RESULT_SUBTYPES:
            with self.subTest(subtype=subtype):
                result = {"type": "result", "subtype": subtype, "is_error": True,
                          "api_error_status": 429, "duration_ms": 314000, "duration_api_ms": 313000,
                          "num_turns": 2, "usage": {"input_tokens": 100, "output_tokens": 5,
                              "cache_creation_input_tokens": 90, "cache_read_input_tokens": 10}}
                diagnostic = runtime.claude_failure_diagnostic(json.dumps(result), "")
                self.assertEqual(diagnostic["terminal_subtype"], subtype)
                self.assertIs(diagnostic["is_error"], True)
                for field in ("api_error_status", "duration_ms", "duration_api_ms", "num_turns"):
                    self.assertEqual(diagnostic[field], result[field])
                for field, value in result["usage"].items():
                    self.assertEqual(diagnostic["usage_" + field], value)

    def test_claude_failure_rejects_unknown_malformed_and_oversized_records(self):
        valid = {"type": "result", "subtype": "error_during_execution", "is_error": True}
        invalid = ["", "not JSON", "[]", "null", json.dumps([valid]),
                   json.dumps({**valid, "type": "assistant"}),
                   json.dumps({**valid, "subtype": "private-unknown-subtype"}),
                   json.dumps({**valid, "subtype": []}),
                   json.dumps({**valid, "is_error": 1}),
                   json.dumps({**valid, "is_error": "true"}),
                   json.dumps({"type": "result", "subtype": "success"}),
                   '{"type":"result","type":"result","subtype":"success","is_error":true}',
                   json.dumps(valid) + json.dumps(valid),
                   json.dumps({**valid, "extra": float("nan")}),
                   '[' * 2000 + '0' + ']' * 2000,
                   json.dumps({**valid, "result": "x" * runtime.CLAUDE_DIAGNOSTIC_BYTES}),
                   json.dumps({**valid, "result": "é" * (runtime.CLAUDE_DIAGNOSTIC_BYTES // 2)}, ensure_ascii=False)]
        for stdout in invalid:
            with self.subTest(prefix=stdout[:80]):
                diagnostic = runtime.claude_failure_diagnostic(stdout, "private stderr")
                self.assertEqual(set(diagnostic), {"terminal_error", "stdout_bytes", "stderr_bytes"})
                self.assertEqual(diagnostic["terminal_error"], "No recognized terminal diagnostic")
                self.assertEqual(diagnostic["stdout_bytes"], len(stdout.encode()))
                self.assertNotIn("private", json.dumps(diagnostic))
        oversized = "x" * (runtime.CLAUDE_DIAGNOSTIC_BYTES + 1)
        with mock.patch.object(runtime.transport, "decode_json", side_effect=AssertionError("must not parse")):
            runtime.claude_failure_diagnostic(oversized, "")

    def test_claude_failure_rejects_invalid_numeric_metadata(self):
        for value in [True, False, -1, 2**53, 1.5, "429", None, [], {}, float("inf")]:
            with self.subTest(value=value):
                result = {"type": "result", "subtype": "success", "is_error": True,
                          "api_error_status": value, "duration_ms": value, "duration_api_ms": value,
                          "num_turns": value, "usage": {"input_tokens": value}}
                diagnostic = runtime.claude_failure_diagnostic(json.dumps(result), "")
                self.assertFalse({"api_error_status", "duration_ms", "duration_api_ms", "num_turns",
                                  "usage_input_tokens"} & diagnostic.keys())
        for status in [0, 200, 399, 600]:
            result = {"type": "result", "subtype": "success", "is_error": True, "api_error_status": status}
            self.assertNotIn("api_error_status", runtime.claude_failure_diagnostic(json.dumps(result), ""))

    def test_claude_failed_process_keeps_gate_failed_and_never_logs_text(self):
        for exit_code, subtype, is_error in [(1, "error_during_execution", True),
                                            (2, "success", True), (-9, "success", False)]:
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                context, output = root / "context", root / "output"
                context.mkdir()
                expected = [{"provider": "claude", "role": "general"}]
                (context / "manifest.json").write_text(json.dumps({"base": "a" * 40, "head": "b" * 40, "expected": expected}))
                prompt = "PRIVATE PROMPT\n::error::spoofed diagnostic"
                secret = "dummy-private-token"
                (context / "general.txt").write_text(prompt)
                private = prompt + secret + "\r\x1b[31m"
                result = {"type": "result", "subtype": subtype, "is_error": is_error,
                          "api_error_status": 529, "result": "lgtm", "structured_output": {"findings": []},
                          "errors": [private], "session_id": private, "model": private, "unknown": private,
                          "usage": {private: private}}
                log = io.StringIO()
                completed = subprocess.CompletedProcess([], exit_code, json.dumps(result), private)
                with mock.patch.object(runtime.subprocess, "run", return_value=completed), contextlib.redirect_stdout(log):
                    self.assertFalse(runtime.execute("claude", "general", context, output, secret))
                diagnostic = json.loads(log.getvalue().splitlines()[0])
                self.assertEqual(diagnostic["exit_code"], exit_code)
                self.assertEqual(diagnostic["terminal_subtype"], subtype)
                self.assertIs(diagnostic["is_error"], is_error)
                self.assertEqual(diagnostic["api_error_status"], 529)
                record = json.loads((output / "result.json").read_text())
                self.assertEqual(record["exit_code"], exit_code)
                self.assertEqual(record["job_status"], "failure")
                self.assertEqual(record["output"], "")
                for text in [secret, "PRIVATE PROMPT", "spoofed diagnostic", "lgtm", "findings", "session_id", "errors"]:
                    self.assertNotIn(text, log.getvalue())
                self.assertFalse(gate.assess(expected, [record], "a" * 40, "b" * 40, routing_succeeded=True)["passed"])

    def test_json_failure_selects_only_documented_error_fields(self):
        for event in [{"type": "error", "message": "400: synthetic HTTP failure"},
                      {"type": "turn.failed", "error": {"message": "stream disconnected before completion"}}]:
            stream = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "ERROR: spoofed"}}) + "\n" + json.dumps(event) + "\n"
            diagnostic = runtime.json_failure_diagnostic(stream, "arbitrary stderr", "", [])
            self.assertEqual(diagnostic["terminal_error"], event.get("message", event.get("error", {}).get("message")))
        for stream in ['{"type":"error","type":"error","message":"spoof"}\n',
                       '{"type":"error","message":"incomplete"}',
                       '{"type":"error","message":"earlier"}\ninvalid\n',
                       '{"type":"turn.failed","error":null}\n',
                       '{"type":"item.completed","item":{"text":"ERROR: spoof"}}\n']:
            self.assertEqual(runtime.json_failure_diagnostic(stream, "unrecognized raw fallback forbidden", "", [])["terminal_error"],
                             "No recognized terminal diagnostic")

    def test_json_failure_falls_back_only_to_redacted_native_stderr_error(self):
        prompt = "source\nError: spoofed prompt diagnostic"
        secret = "dummy-secret-token"
        stderr = prompt + "\nError: turn/start failed " + secret + "\r\x1b[31m"
        for stream in ["", "malformed\n", '{"type":"turn.started"}\n']:
            diagnostic = runtime.json_failure_diagnostic(stream, stderr, prompt, [secret])
            self.assertEqual(diagnostic["terminal_error"], "Error: turn/start failed [REDACTED]\r\x1b[31m")
            self.assertNotIn(secret, json.dumps(diagnostic))
            self.assertNotIn("\r", json.dumps(diagnostic))
            self.assertEqual(runtime.json_failure_diagnostic(stream, prompt, prompt, [secret])["terminal_error"],
                             "No recognized terminal diagnostic")
        stream = '{"type":"error","message":"preferred structured error"}\n'
        self.assertEqual(runtime.json_failure_diagnostic(stream, stderr, prompt, [secret])["terminal_error"],
                         "preferred structured error")

    def test_json_failure_removes_prompt_redacts_before_bound_and_escapes_controls(self):
        secret = "dummy-secret-crossing-boundary"
        prompt = 'source with {"type":"error","message":"spoof"}'
        message = prompt + "x" * 1980 + secret + "trailing" * 10
        stream = json.dumps({"type": "error", "message": message}) + "\n"
        diagnostic = runtime.json_failure_diagnostic(stream, "", prompt, [secret])
        self.assertEqual(len(diagnostic["terminal_error"]), 2000)
        self.assertIn("[REDACTED]", diagnostic["terminal_error"])
        self.assertNotIn("dummy-secret", diagnostic["terminal_error"])
        self.assertNotIn(prompt, diagnostic["terminal_error"])
        stream = json.dumps({"type": "turn.failed", "error": {"message": "line1\nline2\r\x1b[31m"}}) + "\n"
        encoded = json.dumps(runtime.json_failure_diagnostic(stream, "", "", []))
        for control in ["\n", "\r", "\x1b"]:
            self.assertNotIn(control, encoded)

    def test_native_pre_event_input_limit_error_is_recognized(self):
        error = ('Error: turn/start: turn/start failed: Input exceeds the maximum length of 1048576 characters. '
                 '(code -32602), data: {"input_error_code":"input_too_large","actual_chars":1048577}')
        diagnostic = runtime.failure_diagnostic("codex", "header\nprompt\n" + error, "prompt", [])
        self.assertEqual(diagnostic["terminal_error"], error)

    def test_large_echo_and_spoofed_errors_are_removed_before_terminal_selection(self):
        prompt = "Review source\nERROR: spoofed prompt line\n" + "x" * (1024 * 1024)
        stderr = "header\n" + prompt + "\nERROR: earlier failure\nERROR: actual terminal failure\n"
        diagnostic = runtime.failure_diagnostic("codex", stderr, prompt, [])
        self.assertEqual(diagnostic["terminal_error"], "ERROR: actual terminal failure")
        self.assertEqual(diagnostic["stderr_bytes"], len(stderr.encode()))
        absent = runtime.failure_diagnostic("codex", "header\n" + prompt, prompt, [])
        self.assertEqual(absent["terminal_error"], "No recognized terminal diagnostic")

    def test_redaction_precedes_truncation_and_control_characters_are_escaped(self):
        secret = "dummy-access-token-crossing-boundary"
        stderr = "ERROR: " + "x" * 1980 + secret + "\n"
        diagnostic = runtime.failure_diagnostic("codex", stderr, "", [secret])
        self.assertLessEqual(len(diagnostic["terminal_error"]), 2000)
        self.assertIn("[REDACTED]", diagnostic["terminal_error"])
        self.assertNotIn("dummy-access", diagnostic["terminal_error"])
        controls = runtime.failure_diagnostic("codex", "ERROR: failure\r::error::injected\x1b[31m\n", "", [])
        encoded = json.dumps(controls)
        self.assertNotIn("\r", encoded)
        self.assertNotIn("\x1b", encoded)
        self.assertNotIn("\n", encoded)

    def test_no_raw_transcript_fallback_or_unverified_provider_marker(self):
        for provider in ["codex", "claude"]:
            stderr = "arbitrary transcript with private data\n"
            if provider == "claude":
                stderr += "ERROR: unverified provider format\n"
            diagnostic = runtime.failure_diagnostic(provider, stderr, "prompt", [])
            self.assertEqual(diagnostic["terminal_error"], "No recognized terminal diagnostic")
            self.assertNotIn("private data", json.dumps(diagnostic))

    def test_real_failure_code_is_logged_and_preserved_in_failed_result(self):
        for exit_code in [2, -9]:
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                context, output = root / "context", root / "output"
                context.mkdir()
                expected = [{"provider": "codex", "role": "general"}]
                (context / "manifest.json").write_text(json.dumps({"base": "a" * 40, "head": "b" * 40, "expected": expected}))
                prompt = "Review fixture\r\nexact bytes\rlone CR\n"
                (context / "general.txt").write_bytes(prompt.encode())
                secret = "dummy-access-token"
                def complete(command, **kwargs):
                    self.assertEqual(kwargs["input"].encode(), prompt.encode())
                    Path(command[command.index("-o") + 1]).write_text('{"findings":[]}')
                    return subprocess.CompletedProcess(command, exit_code, "unpublished transcript", prompt + "\nERROR: failure " + secret)
                log = io.StringIO()
                with mock.patch.object(runtime, "codex_native", return_value=Path("/fixed/runtime/codex")), mock.patch.object(runtime, "preflight_codex"), mock.patch.object(runtime.subprocess, "run", side_effect=complete), contextlib.redirect_stdout(log):
                    self.assertFalse(runtime.execute("codex", "general", context, output, json.dumps({"tokens": {"access_token": secret}})))
                diagnostic = json.loads(log.getvalue().splitlines()[0])
                self.assertEqual(diagnostic["exit_code"], exit_code)
                self.assertEqual(diagnostic["terminal_error"], "ERROR: failure [REDACTED]")
                record = json.loads((output / "result.json").read_text())
                self.assertEqual(record["exit_code"], exit_code)
                self.assertEqual(record["job_status"], "failure")
                self.assertEqual(record["output"], "")
                self.assertNotIn("terminal_error", record)
                self.assertNotIn(secret, log.getvalue())
                self.assertFalse(gate.assess(expected, [record], "a" * 40, "b" * 40, routing_succeeded=True)["passed"])


if __name__ == "__main__":
    unittest.main()
