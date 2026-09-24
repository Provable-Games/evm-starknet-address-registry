#!/usr/bin/env python3
"""Synthetic loopback Responses smoke for actual pinned exec/resume; no provider review."""

import http.server
import json
from pathlib import Path
import tempfile
import threading
import time

import review_runtime as runtime
import review_transport as transport


def main(aliases=False):
    settings = json.loads((runtime.ROOT / ".github/review/providers.json").read_text())
    version = json.loads((runtime.ROOT / "toolchain.json").read_text())["versions"]["codex"]
    original = "Synthetic original input with α😀 and literal context_compacted text.\n" + "x" * transport.NATIVE_CHARS
    identity = {"base": "a" * 40, "head": "b" * 40}
    requests = []
    mode = ["success"]
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"models":[]}')
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(request)
            if mode[0] == "error":
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"Synthetic failure","type":"invalid_request_error"}}')
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            events = [{"type": "response.created", "response": {"id": "mock-response"}}]
            if mode[0] != "incomplete":
                output = {"part": 1} if len(requests) == 1 else {"findings": []}
                events += [{"type": "response.output_item.done", "item": {"id": "mock-message", "type": "message", "role": "assistant", "phase": "final_answer", "content": [{"type": "output_text", "text": json.dumps(output)}]}},
                           {"type": "response.completed", "response": {"id": "mock-response", "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14}}}]
            for event in events:
                self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
            self.wfile.flush()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with tempfile.TemporaryDirectory(prefix=".ci-review-", dir=runtime.ROOT) as directory:
            private = Path(directory)
            prepared, auth, home = private / "prepared", private / "auth", private / "home"
            for path in [prepared, auth, home]:
                path.mkdir(mode=0o700)
            environment = {"HOME": str(home), "CODEX_HOME": str(auth), "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "CI": "true"}
            # Exercise both native alias regimes regardless of checkout location.
            # This is a synthetic child environment only; production TMPDIR is unchanged.
            temporary = private / "system-tmp" if aliases else private
            temporary.mkdir(exist_ok=True)
            environment["TMPDIR"] = str(temporary)
            config = runtime.codex_config(prepared, auth)
            config = 'model_provider = "mock"\n' + config + f'''
[model_providers.mock]
name = "Synthetic local Responses"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0
'''
            (auth / "config.toml").write_text(config)
            schema = (runtime.ROOT / ".github/review/result.schema.json").read_text()
            (prepared / "schema.json").write_text(schema)
            command = runtime.review_command("codex", settings, prepared, private / "unused.json")
            failures = []
            output = transport.execute_turns(command, original, identity, prepared, auth, environment, version,
                                             settings["codex"]["model"], settings["codex"]["effort"],
                                             lambda result, prompt: failures.append(result.returncode), seconds=60)
            transport.require(json.loads(output) == {"findings": []} and not failures and len(requests) == 2,
                              "Synthetic multi-turn completion failed")
            submitted = transport.chunks_for(original, identity)
            user_text = [part.get("text") for item in requests[-1]["input"] if item.get("role") == "user"
                         for part in item.get("content", []) if part.get("type") == "input_text"]
            transport.require(all(user_text.count(value) == 1 for value in submitted)
                              and user_text.index(submitted[0]) < user_text.index(submitted[1]),
                              "Synthetic resume omitted or reordered full input")
            transport.require(not (auth / "auth.json").exists(), "Synthetic smoke unexpectedly loaded credentials")
            # Exercise native failures through fresh private sessions, not successful verdict mocks.
            for failure_mode in ["error", "incomplete"]:
                failure_auth = private / failure_mode
                failure_auth.mkdir(mode=0o700)
                (failure_auth / "config.toml").write_text(config.replace(str(auth), str(failure_auth)))
                failure_env = {**environment, "CODEX_HOME": str(failure_auth)}
                mode[0] = failure_mode
                failure_final = private / (failure_mode + "-final.json")
                failure_command = runtime.review_command("codex", settings, prepared, failure_final)
                failure_command = [x for x in failure_command[:-1] if x != "--ephemeral"] + ["--json", "-"]
                result = transport.run_bounded(failure_command, "Synthetic failure input", prepared, failure_env,
                                               time.monotonic() + 30, failure_final, failure_auth)
                transport.require(result.returncode != 0, "Synthetic provider failure unexpectedly passed")
                diagnostic = runtime.json_failure_diagnostic(result.stdout, result.stderr, "Synthetic failure input", [])
                transport.require(diagnostic["terminal_error"] != "No recognized terminal diagnostic",
                                  "Synthetic failure lost its structured diagnostic")
                types = [json.loads(line)["type"] for line in result.stdout.splitlines()]
                transport.require("error" in types and "turn.failed" in types and "turn.completed" not in types,
                                  "Synthetic provider failure lacks failed lifecycle")
        transport.require(not private.exists(), "Synthetic session cleanup failed")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    print("Synthetic pinned Codex multi-turn/resume, private history, configured effort and failure checks passed (no provider review).")


if __name__ == "__main__":
    main(aliases=False)
    main(aliases=True)
