import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review_transport as transport
import review_runtime as runtime

THREAD = "00000000-0000-4000-8000-000000000001"
TURN = "00000000-0000-4000-8000-000000000002"
IDENTITY = {"base": "a" * 40, "head": "b" * 40}


def row(kind, payload):
    return {"timestamp": "2026-09-23T00:00:00Z", "type": kind, "payload": payload}


def fixture(auth, prepared, prompt):
    context = {"turn_id": TURN, "root_turn_id": TURN, "cwd": str(prepared), "model": "gpt-6-astra", "approval_policy": "never",
               "collaboration_mode": {"settings": {"reasoning_effort": "medium"}},
               "active_permission_profile": {"id": "registry_review"},
               "permission_profile": {"type": "managed", "network": "restricted", "file_system": {
                   "type": "restricted", "entries": [{"path": {"type": "path", "path": str(auth)}, "access": "deny"}, {"path": {"type": "path", "path": str(prepared)}, "access": "read"}, {"path": {"type": "path", "path": "/fixed/codex"}, "access": "read"}, {"path": {"type": "special", "value": {"kind": "minimal"}}, "access": "read"}]}}}
    user_event = {"type": "item_completed", "thread_id": THREAD, "turn_id": TURN,
                  "item": {"type": "UserMessage", "id": "event-user-id", "content": [{"type": "text", "text": prompt}]}}
    return [row("session_meta", {"id": THREAD, "session_id": THREAD, "cwd": str(prepared), "cli_version": "0.156.0", "source": "exec"}),
            row("event_msg", {"type": "task_started", "turn_id": TURN}),
            row("response_item", {"type": "message", "id": "engine-user-id", "role": "user", "content": [{"type": "input_text", "text": "<environment_context>synthetic</environment_context>"}]}),
            row("turn_context", context),
            row("response_item", {"type": "message", "id": "different-response-id", "role": "user", "content": [{"type": "input_text", "text": prompt}]}),
            row("event_msg", user_event),
            row("response_item", {"type": "function_call", "call_id": "call", "name": "exec_command", "arguments": '{"cmd":"true"}'}),
            row("response_item", {"type": "function_call_output", "call_id": "call", "output": '{"type":"compacted"} is only tool text'}),
            row("event_msg", {"type": "task_complete", "turn_id": TURN})]


class HelperAliasTests(unittest.TestCase):
    def test_exact_owned_alias_directory_and_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); auth = root / "auth"; native = root / "codex"
            native.write_text("synthetic locked executable")
            directory = auth / "tmp/arg0/codex-arg0Ab12cd"
            directory.mkdir(parents=True, mode=0o700)
            directory.parent.chmod(0o700)
            (directory / ".lock").touch()
            for name in transport.HELPER_NAMES:
                (directory / name).symlink_to(native)
            self.assertEqual(transport.inspect_helper_alias(auth, native), directory)
            for mutation in ["target", "extra", "parent", "lock"]:
                with self.subTest(mutation=mutation):
                    if mutation == "target":
                        link = directory / "apply_patch"; link.unlink(); link.symlink_to(root)
                    elif mutation == "extra":
                        link = directory / "secret"; link.touch()
                    elif mutation == "parent":
                        link = directory.parent / "codex-arg0Ef34gh"; link.mkdir()
                    else:
                        link = directory / ".lock"; link.unlink(); link.symlink_to(native)
                    with self.assertRaises(ValueError):transport.inspect_helper_alias(auth, native)
                    if link.is_dir() and not link.is_symlink():link.rmdir()
                    else:link.unlink()
                    if mutation == "target":link.symlink_to(native)
                    elif mutation == "lock":link.touch()


class ChunkTests(unittest.TestCase):
    def test_lossless_unicode_three_part_delivery_and_rendered_bounds(self):
        original = "a" * 750000 + "😀é\n" + "b" * 750000 + "tail"
        turns = transport.chunks_for(original, IDENTITY)
        self.assertEqual(len(turns), 3)
        fragments = []
        for index, turn in enumerate(turns, 1):
            self.assertLessEqual(len(turn), transport.NATIVE_CHARS)
            header = json.loads(turn.splitlines()[1])
            start = turn.index("BEGIN EXACT FRAGMENT (length above)\n") + len("BEGIN EXACT FRAGMENT (length above)\n")
            fragment = turn[start:start + header["content_chars"]]
            self.assertEqual(len(fragment.encode()), header["content_bytes"])
            self.assertEqual(header["part"], index)
            fragments.append(fragment)
        self.assertEqual("".join(fragments).encode(), original.encode())
        self.assertIn('Only acknowledge receipt with {"part":1}', turns[0])
        self.assertIn("All original prompt fragments", turns[-1])
        # The native guard counts scalars, independently from UTF-8 bytes.
        self.assertEqual(transport.text_input("😀" * transport.NATIVE_CHARS), "😀" * transport.NATIVE_CHARS)
        for text in ["x" * (transport.NATIVE_CHARS + 1), "\ud800"]:
            with self.assertRaises((ValueError, UnicodeError)):
                transport.text_input(text)
        with self.assertRaises(ValueError):
            transport.chunks_for("x" * (2 * 1024 * 1024 + 1), IDENTITY)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth, self.prepared = root / "auth", root / "prepared"
        self.auth.mkdir(); self.prepared.mkdir()
        directory = self.auth / "sessions/2026/09/23"
        directory.mkdir(parents=True)
        self.path = directory / f"rollout-2026-09-23T00-00-00-{THREAD}.jsonl"
        self.prompt = 'exact source with {"type":"compacted"} and ContextCompaction text'
        self.rows = fixture(self.auth, self.prepared, self.prompt)

    def check(self, rows=None, previous=b""):
        data = b"".join((json.dumps(value) + "\n").encode() for value in (self.rows if rows is None else rows))
        self.path.write_bytes(data)
        return transport.validate_history(self.auth, THREAD, previous, [self.prompt], self.prepared, "gpt-6-astra", "medium", "0.156.0", Path("/fixed/codex"))

    def test_only_verified_per_turn_helper_read_grant_is_accepted(self):
        alias = self.auth / "tmp/arg0/codex-arg0Ab12cd"
        entry = {"path": {"type": "path", "path": str(alias)}, "access": "read"}
        self.rows[3]["payload"]["permission_profile"]["file_system"]["entries"].append(entry)
        self.path.write_text("".join(json.dumps(value) + "\n" for value in self.rows))
        arguments = (self.auth, THREAD, b"", [self.prompt], self.prepared, "gpt-6-astra", "medium", "0.156.0", Path("/fixed/codex"))
        transport.validate_history(*arguments, [alias])
        for wrong in [None, alias.parent, alias.with_name("codex-arg0Ef34gh")]:
            with self.assertRaises(ValueError):transport.validate_history(*arguments, [wrong])
        entry["access"] = "write"
        self.path.write_text("".join(json.dumps(value) + "\n" for value in self.rows))
        with self.assertRaises(ValueError):transport.validate_history(*arguments, [alias])

    def test_exact_typed_payload_binding_accepts_engine_messages_and_different_ids(self):
        self.check()
        rows = copy.deepcopy(self.rows)
        # Engine context is not required to occur at a special position.
        engine = rows.pop(2)
        rows.insert(5, engine)
        self.check(rows)

    def test_compaction_in_every_typed_location_rejects_completed_review(self):
        markers = [row("compacted", {}), row("response_item", {"type": "compaction", "encrypted_content": "x"}),
                   row("response_item", {"type": "context_compaction"}), row("event_msg", {"type": "context_compacted"}),
                   row("event_msg", {"type": "item_completed", "thread_id": THREAD, "turn_id": TURN,
                       "item": {"type": "ContextCompaction", "id": "compacted-item"}})]
        for marker in markers:
            with self.subTest(marker=marker), self.assertRaises(ValueError):
                self.check(self.rows[:-1] + [marker, self.rows[-1]])

    def test_missing_duplicate_altered_fragment_and_lifecycle_fail(self):
        variants = []
        for index in [0, 1, 3, 4, 5, len(self.rows) - 1]:
            variants.append(self.rows[:index] + self.rows[index + 1:])
        for index in [0, 1, 4, 5, len(self.rows) - 1]:
            variants.append(self.rows[:index] + [self.rows[index]] + self.rows[index:])
        changed = copy.deepcopy(self.rows); changed[5]["payload"]["thread_id"] = TURN; variants.append(changed)
        changed = copy.deepcopy(self.rows); changed[4]["payload"]["content"][0]["text"] = "wrong"; variants.append(changed)
        changed = copy.deepcopy(self.rows); changed[-1]["payload"]["error"] = {"message": "failure"}; variants.append(changed)
        variants.append(self.rows[:-1] + [row("event_msg", {"type": "future_lifecycle"}), self.rows[-1]])
        for rows in variants:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.check(rows)

    def test_session_settings_or_history_mutation_fail(self):
        for field, value in [("id", TURN), ("session_id", TURN), ("cwd", "/elsewhere"), ("cli_version", "0.0.0"), ("parent_thread_id", TURN)]:
            rows = copy.deepcopy(self.rows); rows[0]["payload"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):self.check(rows)
        for field in ["turn_id", "root_turn_id"]:
            rows = copy.deepcopy(self.rows); rows[3]["payload"][field] = THREAD
            with self.subTest(field=field), self.assertRaises(ValueError):self.check(rows)
        for access in ["read", "write"]:
            rows = copy.deepcopy(self.rows)
            rows[3]["payload"]["permission_profile"]["file_system"]["entries"].append(
                {"path": {"type": "path", "path": "/"}, "access": access})
            with self.subTest(access=access), self.assertRaises(ValueError):self.check(rows)
        with self.assertRaises(ValueError):self.check(previous=b"different prior content")
        for raw in [b'{"type":"session_meta"', b'null\n', b'{"type":"session_meta","type":"compacted"}\n']:
            self.path.write_bytes(raw)
            with self.assertRaises(ValueError):
                transport.validate_history(self.auth, THREAD, b"", [self.prompt], self.prepared, "gpt-6-astra", "medium", "0.156.0", Path("/fixed/codex"))
        self.path.unlink(); self.path.symlink_to(self.prepared / "unrelated")
        with self.assertRaises(ValueError):
            transport.validate_history(self.auth, THREAD, b"", [self.prompt], self.prepared, "gpt-6-astra", "medium", "0.156.0", Path("/fixed/codex"))

    def test_known_shell_record_shapes_do_not_treat_tool_text_as_lifecycle(self):
        tool = row("event_msg", {"type": "item_completed", "thread_id": THREAD, "turn_id": TURN,
                   "item": {"type": "CommandExecution", "id": "shell", "command": ["/bin/sh", "-c", "true"],
                            "cwd": str(self.prepared), "status": "completed", "aggregated_output": "ContextCompaction"}})
        self.check(self.rows[:-1] + [tool, self.rows[-1]])
        tool["payload"]["item"]["command"] = "wrong shape"
        with self.assertRaises(ValueError):self.check(self.rows[:-1] + [tool, self.rows[-1]])


class LifecycleTests(unittest.TestCase):
    def events(self):
        return [{"type": "thread.started", "thread_id": THREAD}, {"type": "turn.started"},
                {"type": "item.completed", "item": {"type": "agent_message", "id": "final", "text": '{"findings":[]}'}},
                {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}}]

    def test_only_exact_successful_final_lifecycle_is_accepted(self):
        events = self.events()
        encode = lambda values: "".join(json.dumps(value) + "\n" for value in values)
        self.assertEqual(transport.validate_events(encode(events), THREAD, '{"findings":[]}'), THREAD)
        variants = [events[:-1], events + [events[-1]], events[1:], [events[1], events[0]] + events[2:],
                    events[:-1] + [{"type": "turn.failed", "error": {"message": "failure"}}],
                    events[:-1] + [{"type": "error", "message": "failure"}],
                    events[:-1] + [{"type": "future.event"}]]
        for variant in variants:
            with self.subTest(events=variant), self.assertRaises(ValueError):
                transport.validate_events(encode(variant), THREAD, '{"findings":[]}')
        with self.assertRaises(ValueError):transport.validate_events(encode(events), TURN, '{"findings":[]}')
        with self.assertRaises(ValueError):transport.validate_events(encode(events), THREAD, 'lgtm')
        tool = {"type": "item.started", "item": {"id": "shell", "type": "command_execution", "command": "true", "aggregated_output": "", "status": "in_progress"}}
        with self.assertRaises(ValueError):transport.validate_events(encode(events[:2] + [tool] + events[2:]), THREAD, '{"findings":[]}')
        done = copy.deepcopy(tool); done["type"] = "item.completed"; done["item"]["status"] = "completed"
        transport.validate_events(encode(events[:2] + [tool, done] + events[2:]), THREAD, '{"findings":[]}')

    def test_shared_deadline_and_ack_never_become_final_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); prepared, auth = root / "prepared", root / "auth"
            prepared.mkdir(); auth.mkdir(); (prepared / "schema.json").write_text('{}')
            command = ["codex", "exec", "--ephemeral", "--output-schema", str(prepared / "schema.json"), "-o", str(root / "unused"), "-"]
            clock, calls = [0], []
            def process(args, prompt, cwd, environment, deadline, final, home, verify_alias=False):
                calls.append((args, deadline)); clock[0] += 3
                final.write_text(json.dumps({"part": len(calls)}))
                result = subprocess.CompletedProcess(args, 0, "events", ""); result.helper_alias = None
                return result
            with mock.patch.object(transport.time, "monotonic", side_effect=lambda: clock[0]), mock.patch.object(transport, "run_bounded", side_effect=process), mock.patch.object(transport, "validate_events", return_value=THREAD), mock.patch.object(transport, "validate_history", return_value=b"history"):
                with self.assertRaisesRegex(ValueError, "deadline"):
                    transport.execute_turns(command, "x" * (2 * 1024 * 1024), IDENTITY, prepared, auth, {}, "0.156.0", "gpt-6-astra", "medium", lambda *_: None, seconds=7)
            self.assertEqual(len(calls), 2)
            self.assertEqual([deadline for _, deadline in calls], [7, 7])
            self.assertNotIn("--ephemeral", calls[0][0]); self.assertEqual(calls[1][0][-3:], ["resume", THREAD, "-"])

    def test_bad_ack_and_nonzero_exit_stop_before_next_fragment(self):
        for answer, code in [('lgtm', 0), ('{"findings":[]}', 0), ('{"part":true}', 0), ('{"part":2}', 0), ('{"part":1}', -9)]:
            with self.subTest(answer=answer, code=code), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); prepared, auth = root / "prepared", root / "auth"
                prepared.mkdir(); auth.mkdir(); (prepared / "schema.json").write_text('{}')
                command = ["codex", "exec", "--ephemeral", "-o", str(root / "unused"), "-"]
                failures = []
                def process(args, prompt, cwd, environment, deadline, final, home, verify_alias=False):
                    final.write_text(answer)
                    result = subprocess.CompletedProcess(args, code, "events", ""); result.helper_alias = None
                    return result
                with mock.patch.object(transport, "run_bounded", side_effect=process) as run, mock.patch.object(transport, "validate_events", return_value=THREAD), mock.patch.object(transport, "validate_history", return_value=b"history"):
                    with self.assertRaises(ValueError):
                        transport.execute_turns(command, "x" * (transport.NATIVE_CHARS + 1), IDENTITY, prepared, auth, {}, "0.156.0", "gpt-6-astra", "medium", lambda result, _: failures.append(result.returncode))
                self.assertEqual(run.call_count, 1)
                self.assertEqual(failures, [code] if code else [])


class ResourceTests(unittest.TestCase):
    def test_final_file_and_history_limits_stop_live_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); auth = root / "auth"; auth.mkdir()
            for target in [root / "final", auth / "sessions/rollout-large.jsonl"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                code = f'import pathlib,time; pathlib.Path({str(target)!r}).write_bytes(b"x" * 5000); time.sleep(30)'
                with mock.patch.object(transport, "MAX_BYTES", 4096), mock.patch.object(transport, "MAX_FINAL_BYTES", 4096), self.assertRaisesRegex(ValueError, "bound"):
                    transport.run_bounded([sys.executable, "-c", code], "input", root, os.environ.copy(), time.monotonic() + 10, root / "final", auth)
                target.unlink()

    def test_output_bound_kills_process_and_timeout_kills_descendant(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); auth = root / "auth"; auth.mkdir()
            with mock.patch.object(transport, "MAX_BYTES", 4096), self.assertRaisesRegex(ValueError, "output exceeds"):
                transport.run_bounded([sys.executable, '-c', 'print("x" * 100000)'], "input", root, os.environ.copy(), time.monotonic() + 10, root / "final", auth)
            script = 'import subprocess,time,pathlib; p=subprocess.Popen(["' + sys.executable + '","-c","import time; time.sleep(30)"]); pathlib.Path("child.pid").write_text(str(p.pid)); time.sleep(30)'
            with self.assertRaisesRegex(ValueError, "deadline"):
                transport.run_bounded([sys.executable, '-c', script], "input", root, os.environ.copy(), time.monotonic() + 3, root / "final", auth)
            pid = int((root / "child.pid").read_text())
            stat = Path(f"/proc/{pid}/stat")
            if stat.exists():self.assertEqual(stat.read_text().split()[2], "Z")

    def test_bounded_private_files_and_multiturn_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); p = root / "large"; p.write_bytes(b"x" * 20)
            with self.assertRaises(ValueError):transport.read_bounded(p, 10)
            context = root / "context"; context.mkdir()
            (context / "manifest.json").write_text(json.dumps({**IDENTITY, "expected": [{"provider": "codex", "role": "general"}]}))
            (context / "general.txt").write_text("x" * (transport.NATIVE_CHARS + 1))
            paths = []
            def fail(command, prompt, identity, prepared, auth, *args):
                paths.append(auth.parent)
                raise ValueError("Synthetic transport failure")
            with mock.patch.object(runtime, "codex_native", return_value=Path('/fixed/codex')), mock.patch.object(runtime, "preflight_codex"), mock.patch.object(transport, "execute_turns", side_effect=fail):
                self.assertFalse(runtime.execute("codex", "general", context, root / "output", '{"tokens":{"access_token":"dummy-token"}}'))
            self.assertTrue(paths)
            self.assertTrue(all(not path.exists() for path in paths))
            self.assertEqual(json.loads((root / "output/result.json").read_text())["job_status"], "failure")


if __name__ == "__main__":
    unittest.main()
