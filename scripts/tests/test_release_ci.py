"""Guard required integration CI coverage of the local release path."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/release"))
from check_ci_records import check  # noqa: E402


class ReleaseCiTests(unittest.TestCase):
    def test_required_integration_job_invokes_release_checks_in_order(self):
        workflow = (ROOT / ".github/workflows/cairo.yml").read_text()
        job = workflow.split("  integration:\n", 1)[1].split("  required:\n", 1)[0]
        commands = [
            "scripts/release/class-hash.mjs --max-warnings=0",
            "python3 scripts/release/test_local.py",
            "python3 scripts/release/local.py deploy-local",
            "npm run check:package -- --output",
            "python3 scripts/release/check_ci_records.py",
        ]
        positions = [job.index(command) for command in commands]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("mkdir -p .tools/release-records", job)
        self.assertIn("'scripts/release/*.{mts,mjs}'", job)
        for path in ["ci-local-deployment.json", "ci-checked-sdk/checked-package.json",
                     "ci-checked-sdk/provable-games-evm-starknet-address-registry-0.0.0.tgz"]:
            self.assertIn(path, job)
        self.assertIn("needs: [scope, lint, test, evidence, integration]", workflow)

    def test_record_check_rejects_archive_change_and_incomplete_deployment(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            package_dir = directory / "package"
            package_dir.mkdir()
            deployment_path = directory / "deployment.json"
            source = {"revision": "reviewed-head", "dirty": False}
            deployment = {
                "kind": "local-deployment-success", "environment": "local-devnet",
                "source": source, "server_stopped": "-15",
                "authenticated_readback": {"native_version": "49", "block": {"blockHash": "0x1"},
                                           "receipts": [{"status": "succeeded"}, {"status": "succeeded"}]},
            }
            archive = b"checked bytes"
            digest = hashlib.sha256(archive).hexdigest()
            package = {"kind": "local-checked-sdk-pack",
                       "archive": {"filename": "sdk.tgz", "bytes": len(archive), "sha256": digest},
                       "evidence": {"source": source, "archive_sha256": digest}}
            deployment_path.write_text(json.dumps(deployment))
            (package_dir / "checked-package.json").write_text(json.dumps(package))
            (package_dir / "sdk.tgz").write_bytes(archive)
            check(deployment_path, package_dir, "reviewed-head")
            for status in ("-9", "0"):
                deployment["server_stopped"] = status
                deployment_path.write_text(json.dumps(deployment))
                check(deployment_path, package_dir, "reviewed-head")
            deployment["server_stopped"] = "running"
            deployment_path.write_text(json.dumps(deployment))
            with self.assertRaisesRegex(ValueError, "did not report cleanup"):
                check(deployment_path, package_dir, "reviewed-head")
            deployment["server_stopped"] = "-15"
            deployment_path.write_text(json.dumps(deployment))
            (package_dir / "sdk.tgz").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Retained archive differs"):
                check(deployment_path, package_dir, "reviewed-head")
            (package_dir / "sdk.tgz").write_bytes(archive)
            deployment["authenticated_readback"]["receipts"][0]["status"] = "reverted"
            deployment_path.write_text(json.dumps(deployment))
            with self.assertRaisesRegex(ValueError, "receipts must succeed"):
                check(deployment_path, package_dir, "reviewed-head")


if __name__ == "__main__":
    unittest.main()
