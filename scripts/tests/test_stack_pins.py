import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_bootstrap as gate


class StackPinTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "packages/sdk").mkdir(parents=True)
        self.manifest = {
            "versions": {"npm": "12.1.0", "node": "26.10.0", "node_lts": "24.21.0"},
            "packages": {"fixture": {"version": "1.0.0", "integrity": "sha512-fixture"}},
        }
        self.engines = {"node": "^24.21.0 || ^26.10.0", "npm": "12.1.0"}
        self.package = {"private": True, "packageManager": "npm@12.1.0", "engines": self.engines,
                        "workspaces": ["packages/sdk"], "devDependencies": {"fixture": "1.0.0"}}
        self.lock = {"packages": {"": {"engines": self.engines},
                                 "node_modules/fixture": self.manifest["packages"]["fixture"]}}
        self.write("package.json", self.package)
        self.write("package-lock.json", self.lock)
        self.write("packages/sdk/package.json", {"private": True})

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def check(self):
        with mock.patch.object(gate, "ROOT", self.root):
            gate.check_stack_pins(self.manifest)

    def test_reserved_pin_is_optional_until_any_transitive_resolution_exists(self):
        self.manifest["packages"]["rolldown"] = {"version": "1.2.9", "integrity": "sha512-reserved"}
        self.check()  # No installed resolution is required for a reserved pin.
        for key in ["node_modules/rolldown", "node_modules/parent/node_modules/rolldown"]:
            with self.subTest(key=key):
                lock = copy.deepcopy(self.lock)
                lock["packages"][key] = {"version": "1.2.9", "integrity": "sha512-reserved"}
                self.write("package-lock.json", lock)
                self.check()
                lock["packages"][key]["version"] = "1.2.8"
                self.write("package-lock.json", lock)
                with self.assertRaisesRegex(ValueError, "Node lock differs"):
                    self.check()
        self.write("package-lock.json", self.lock)

    def test_transitive_pin_requires_exact_integrity_at_root_and_nested_paths(self):
        self.manifest["packages"]["rolldown"] = {"version": "1.2.9", "integrity": "sha512-reserved"}
        for key in ["node_modules/rolldown", "node_modules/parent/node_modules/rolldown"]:
            for integrity in [None, "sha512-different"]:
                with self.subTest(key=key, integrity=integrity):
                    lock = copy.deepcopy(self.lock)
                    entry = {"version": "1.2.9"}
                    if integrity is not None:
                        entry["integrity"] = integrity
                    lock["packages"][key] = entry
                    self.write("package-lock.json", lock)
                    with self.assertRaisesRegex(ValueError, "Node lock differs"):
                        self.check()

    def test_unreviewed_workspace_and_missing_manifest_fail(self):
        self.check()
        self.write("package.json", {**self.package, "workspaces": ["packages/sdk", "packages/extra"]})
        with self.assertRaisesRegex(ValueError, "Workspace inventory"):
            self.check()
        self.write("package.json", self.package)
        (self.root / "packages/sdk/package.json").unlink()
        with self.assertRaisesRegex(ValueError, "SDK manifest"):
            self.check()

    def test_nested_resolution_cannot_hide_a_different_integrity(self):
        lock = copy.deepcopy(self.lock)
        lock["packages"]["packages/sdk/node_modules/fixture"] = {
            "version": "1.0.0", "integrity": "sha512-different-content"}
        self.write("package-lock.json", lock)
        with self.assertRaisesRegex(ValueError, "packages/sdk/node_modules/fixture"):
            self.check()

    def test_direct_dependency_ranges_and_unapproved_packages_fail(self):
        for dependencies in [{"fixture": "^1.0.0"}, {"unapproved": "1.0.0"}]:
            with self.subTest(dependencies=dependencies):
                self.write("package.json", {**self.package, "devDependencies": dependencies})
                with self.assertRaisesRegex(ValueError, "Unapproved direct Node dependency"):
                    self.check()

    def test_cairo_source_requires_its_separate_verified_pins(self):
        (self.root / "contracts").mkdir()
        (self.root / "contracts/Scarb.toml").write_text('[package]\nname="fixture"\n')
        with self.assertRaisesRegex(ValueError, "cairo_packages"):
            self.check()

    def test_cairo_pin_metadata_rejects_missing_and_invalid_fields(self):
        (self.root / "contracts").mkdir()
        (self.root / "contracts/Scarb.toml").write_text('[package]\nname="contracts"\n')
        valid = {"version": "0.64.0", "registry": "https://scarbs.xyz/", "sha256": "a" * 64}
        invalid = [None, {}]
        invalid.extend({key: value for key, value in valid.items() if key != missing}
                       for missing in valid)
        for key, value in [("version", "^0.64.0"), ("version", "0.64.0-rc.1"),
                           ("registry", "http://scarbs.xyz/"), ("registry", "https://example.com/"),
                           ("sha256", "z" * 64), ("sha256", "a" * 63), ("sha256", None)]:
            invalid.append({**valid, key: value})
        for pin in invalid:
            with self.subTest(pin=pin):
                self.manifest["cairo_packages"] = {"snforge_std": pin}
                with self.assertRaisesRegex(ValueError, "Invalid cairo_packages pin: snforge_std"):
                    self.check()

    def test_cairo_integrity_and_fatal_warnings_are_required(self):
        (self.root / "contracts").mkdir()
        self.manifest["versions"].update(cairo="2.20.0", starknet_foundry="0.64.0")
        self.manifest["cairo_packages"] = {"snforge_std": {
            "version": "0.64.0", "registry": "https://scarbs.xyz/", "sha256": "a" * 64}}
        manifest = '''[package]
name = "contracts"
cairo-version = "=2.20.0"
[dependencies]
starknet = "=2.20.0"
[dev-dependencies]
snforge_std = "=0.64.0"
[scripts]
test = "snforge test"
[cairo]
allow-warnings = false
[tool.snforge]
fuzzer_runs = 256
'''
        lock = '''[[package]]
name = "snforge_std"
version = "0.64.0"
source = "registry+https://scarbs.xyz/"
checksum = "sha256:CHECKSUM"
'''.replace("CHECKSUM", "a" * 64)
        manifest_path = self.root / "contracts/Scarb.toml"
        lock_path = self.root / "contracts/Scarb.lock"
        manifest_path.write_text(manifest)
        lock_path.write_text(lock)
        self.check()
        lock_path.write_text(lock.replace("a" * 64, "b" * 64))
        with self.assertRaisesRegex(ValueError, "Unapproved Cairo lock entry"):
            self.check()
        lock_path.write_text(lock)
        manifest_path.write_text(manifest.replace("allow-warnings = false", "allow-warnings = true"))
        with self.assertRaisesRegex(ValueError, "warnings must be fatal"):
            self.check()
        for replacement in [manifest.replace("fuzzer_runs = 256", "fuzzer_runs = 1"),
                            manifest.replace("[tool.snforge]", "[tool.snforge]\nfuzzer_seed = 20260907")]:
            manifest_path.write_text(replacement)
            with self.assertRaisesRegex(ValueError, "fuzz settings"):
                self.check()
        for bad_script in [manifest.replace('test = "snforge test"', 'test = "snforge test --profile coverage"'),
                           manifest.replace('test = "snforge test"', 'test = "echo mock-summary"'),
                           manifest.replace('test = "snforge test"', 'test = "snforge test --exact nonexistent"'),
                           manifest.replace('[scripts]\ntest = "snforge test"\n', '')]:
            manifest_path.write_text(bad_script)
            with self.assertRaisesRegex(ValueError, "test script must be exactly snforge test"):
                self.check()
        manifest_path.write_text(manifest)
        for bad_lock in [lock.replace('source = "registry+https://scarbs.xyz/"\n', ''),
                         lock.replace('checksum = "sha256:' + "a" * 64 + '"\n', ''),
                         lock + '\n[[package]]\nname = "unapproved_path"\nversion = "1.0.0"\n']:
            lock_path.write_text(bad_lock)
            with self.assertRaisesRegex(ValueError, "Unapproved Cairo lock entry"):
                self.check()
        lock_path.write_text(lock + '\n[[package]]\nname = "contracts"\nversion = "0.1.0"\n')
        self.check()


if __name__ == "__main__":
    unittest.main()
