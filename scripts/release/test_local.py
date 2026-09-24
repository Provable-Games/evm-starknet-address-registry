"""Release safety boundaries; real deployment is a separate explicit command."""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import local

CONFIG = json.loads((Path(__file__).parent / "local.example.json").read_text())


class LocalReleaseTests(unittest.TestCase):
    def test_pinned_tool_version_rejects_suffixes_and_other_output(self):
        for tool, output, pin in [
            ("node", "v26.10.0", "26.10.0"),
            ("npm", "12.1.0", "12.1.0"),
            ("scarb", "scarb 2.20.1 (reviewed build)", "2.20.1"),
            ("sncast", "sncast 0.64.0", "0.64.0"),
            ("universal-sierra-compiler", "universal-sierra-compiler 2.10.1", "2.10.1"),
            ("starknet-devnet", "starknet-devnet 0.10.0", "0.10.0"),
        ]:
            with self.subTest(tool=tool):
                local.require_pinned_version(tool, output, pin)
                for altered in [output.replace(pin, pin + "-beta", 1),
                                output.replace(pin, pin + "+custom", 1),
                                "other-tool " + pin, ""]:
                    with self.subTest(altered=altered), self.assertRaisesRegex(ValueError, "expected manifest pin"):
                        local.require_pinned_version(tool, altered, pin)

    def test_public_endpoint_and_environment_refused(self):
        for extra in [{"rpc_url": "https://starknet-mainnet.example/rpc"}, {"rpc_url": "http://127.0.0.1:5050/rpc"}, {"private_key": "1"}, {"environment": "sepolia"}]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                local.validate_config({**CONFIG, **extra})

    def test_invalid_config(self):
        for key, values in {"schema_version": [True, 2], "ethereum_chain_id": [11155111, "1"], "account_chain_id": ["SN_MAIN"], "account_label": ["", "a" * 49, " Two", "Two  Words", "Two-words", "é", "Two\n"]}.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    local.validate_config({**CONFIG, key: value})
        self.assertEqual(local.validate_config(CONFIG), CONFIG)

    def test_full_cairo_bytearray_label(self):
        for label in ["A", "A" * 31, "A" * 48]:
            data = local.constructor(local.validate_config({**CONFIG, "account_label": label}))
            count = int(data[2])
            decoded = b"".join(int(word).to_bytes(31, "big") for word in data[3:3 + count])
            decoded += int(data[-2]).to_bytes(int(data[-1]), "big")
            self.assertEqual(decoded.decode(), label)

    def test_exclusive_file_symlink_and_concurrent_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            local.exclusive_json(path, {"first": True})
            with self.assertRaises(FileExistsError):
                local.exclusive_json(path, {"second": True})
            self.assertEqual(json.loads(path.read_text()), {"first": True})
            link = Path(directory) / "link.json"
            link.symlink_to(Path(directory) / "missing")
            with self.assertRaises(FileExistsError):
                local.exclusive_json(link, {})
            self.assertTrue(link.is_symlink())
            raced = Path(directory) / "race.json"
            original = local.os.link
            def race(source, target):
                target.write_text("concurrent writer")
                original(source, target)
            with patch.object(local.os, "link", side_effect=race), self.assertRaises(FileExistsError):
                local.exclusive_json(raced, {})
            self.assertEqual(raced.read_text(), "concurrent writer")
            self.assertFalse(list(Path(directory).glob(".local-release-*")))

    def test_plan_never_starts_server_or_publishes_success(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            output = Path(directory) / "plan.json"
            config.write_text(json.dumps(CONFIG))
            with patch.object(local, "prepare", return_value={"kind": "local-deployment-plan"}), patch.object(local, "local_deployment") as session:
                local.main(["plan", "--config", str(config), "--output", str(output)])
            session.assert_not_called()
            self.assertEqual(json.loads(output.read_text())["kind"], "local-deployment-plan")

    def test_failed_receipt_or_readback_never_publishes_success(self):
        for fail_receipt in [False, True]:
            with self.subTest(fail_receipt=fail_receipt), tempfile.TemporaryDirectory() as directory:
                evidence = Path(directory)
                output = evidence / "success.json"
                stopped = []
                @contextmanager
                def failed_session(**kwargs):
                    try:
                        if fail_receipt:
                            raise RuntimeError("receipt failed")
                        def failed_readback(*args):
                            raise RuntimeError("readback mismatch")
                        yield evidence, {}, failed_readback
                    finally:
                        stopped.append(True)
                plan = {"config": CONFIG, "identity": {"class_hash": "0x1"}, "constructor_calldata": [], "artifact_sha256": {}}
                with patch.object(local, "local_deployment", failed_session), self.assertRaises(RuntimeError):
                    local.deploy(copy.deepcopy(plan), output)
                self.assertEqual(stopped, [True])
                self.assertFalse(output.exists())

    def test_source_change_after_readback_refuses_success_after_cleanup(self):
        initial = {"revision": "reviewed", "dirty": False, "sha256": {"readback.ts": "before"}}
        for changed in [
            {**initial, "revision": "different"},
            {**initial, "dirty": True},
            {**initial, "sha256": {"readback.ts": "after"}},
        ]:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                evidence = Path(directory)
                output = evidence / "success.json"
                stopped = []
                current = copy.deepcopy(initial)
                @contextmanager
                def session(**kwargs):
                    try:
                        def readback(*args):
                            current.clear()
                            current.update(changed)
                            return '{}'
                        yield evidence, {}, readback
                    finally:
                        stopped.append(True)
                        (evidence / "server-stopped.txt").write_text("-15")
                def identity_after_cleanup():
                    self.assertEqual(stopped, [True])
                    return current
                plan = {"config": CONFIG, "identity": {"class_hash": "0x1"},
                        "constructor_calldata": [], "artifact_sha256": {}, "source": initial}
                with patch.object(local, "local_deployment", session), patch.object(local, "source_identity", side_effect=identity_after_cleanup), self.assertRaisesRegex(ValueError, "Source identity changed"):
                    local.deploy(plan, output)
                self.assertFalse(output.exists())
                self.assertEqual(stopped, [True])
                self.assertEqual((evidence / "server-stopped.txt").read_text(), "-15")


if __name__ == "__main__":
    unittest.main()
