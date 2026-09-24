import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import setup_reference


class ReferenceSetupTests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(setup_reference.LOCK.read_text())
        self.manifest = json.loads((setup_reference.ROOT / "toolchain.json").read_text())
        self.requirements = (setup_reference.ROOT / "scripts/reference/requirements.lock").read_text()

    def validate(self, lock=None, requirements=None):
        setup_reference.validate_lock(lock or self.lock, self.manifest,
                                      self.requirements if requirements is None else requirements)

    def test_interrupted_creation_remains_owned_and_retries_at_final_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "reference-venv"
            identity = {"format": 1, "lock_sha256": "synthetic"}
            def interrupted(command, **kwargs):
                self.assertEqual(command[-1], str(destination))
                self.assertEqual(json.loads((destination / ".registry-reference.json").read_text()), identity)
                (destination / "partial").write_text("interrupted")
                raise KeyboardInterrupt()
            with patch.object(setup_reference.subprocess, "run", side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    setup_reference.create_environment(Path("/private/python"), destination, identity, {})
            def completed(command, **kwargs):
                self.assertEqual(command[-1], str(destination))
                self.assertFalse((destination / "partial").exists())
                self.assertEqual({p.name for p in destination.iterdir()}, {".registry-reference.json"})
                (destination / "pyvenv.cfg").write_text("created at " + str(destination))
            with patch.object(setup_reference.subprocess, "run", side_effect=completed):
                setup_reference.create_environment(Path("/private/python"), destination, identity, {})
            self.assertIn(str(destination), (destination / "pyvenv.cfg").read_text())
            self.assertEqual({p.name for p in destination.parent.iterdir()}, {"reference-venv"})

    def test_unmanaged_and_redirected_destinations_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for kind in ["empty", "nonempty", "invalid-marker", "symlink"]:
                with self.subTest(kind=kind):
                    destination = root / kind
                    if kind == "symlink":
                        destination.symlink_to(root / "nonempty", target_is_directory=True)
                    else:
                        destination.mkdir()
                        if kind != "empty":(destination / "keep").write_text("unmanaged")
                        if kind == "invalid-marker":(destination / ".registry-reference.json").write_text('{"format":2}')
                    with patch.object(setup_reference.subprocess, "run") as run:
                        with self.assertRaisesRegex(ValueError, "unmanaged"):
                            setup_reference.create_environment(Path("/private/python"), destination, {"format": 1}, {})
                    run.assert_not_called()
                    self.assertTrue(destination.exists())
                    if kind != "empty":self.assertEqual((destination / "keep").read_text(), "unmanaged")

    def test_committed_projection(self):
        self.validate()

    def test_missing_architecture_rejected(self):
        lock = copy.deepcopy(self.lock)
        del lock["packages"]["eth-account"]["wheels"]["linux-arm64"]
        with self.assertRaisesRegex(ValueError, "architectures"):
            self.validate(lock)

    def test_projection_cannot_omit_package(self):
        with self.assertRaisesRegex(ValueError, "projection"):
            self.validate(requirements="\n".join(self.requirements.splitlines()[:-1]) + "\n")

    def test_wheel_source_and_hash_rejected(self):
        for field, value in [("url", "https://untrusted.invalid/wheel.whl"), ("sha256", "0"),
                             ("filename", "../escape.whl")]:
            lock = copy.deepcopy(self.lock)
            lock["packages"]["eth-account"]["wheels"]["linux-x64"][field] = value
            with self.assertRaisesRegex(ValueError, "official source"):
                self.validate(lock)

    def test_cached_wheel_is_reverified_without_network(self):
        payload = b"verified test wheel"
        digest = hashlib.sha256(payload).hexdigest()
        artifact = {"url": "https://files.pythonhosted.org/example.whl", "filename": "example.whl", "sha256": digest}
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            target = cache / digest / artifact["filename"]
            target.parent.mkdir()
            target.write_bytes(payload)
            with patch("setup_reference.urllib.request.urlopen", side_effect=AssertionError("network used")):
                self.assertEqual(setup_reference.wheel(artifact, cache), target)
                target.write_bytes(b"corruption")
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    setup_reference.wheel(artifact, cache)

    def test_environment_excludes_host_python_and_pip_overrides(self):
        with patch.dict("os.environ", {"PYTHONPATH": "/host", "PYTHONHOME": "/host", "PIP_INDEX_URL": "bad"}):
            result = setup_reference.environment()
        self.assertNotIn("PYTHONPATH", result)
        self.assertNotIn("PYTHONHOME", result)
        self.assertNotIn("PIP_INDEX_URL", result)
        self.assertEqual(result["PIP_CONFIG_FILE"], "/dev/null")


if __name__ == "__main__":
    unittest.main()
