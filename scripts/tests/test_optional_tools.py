import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_bootstrap
import setup


class OptionalToolsTests(unittest.TestCase):
    def test_optional_release_sources_match_version_and_architecture(self):
        manifest = json.loads((setup.ROOT / "toolchain.json").read_text())
        check_bootstrap.check_optional_tools(manifest)
        for tool in ["cairo-coverage", "starknet-devnet"]:
            for mutation in ["missing_arch", "wrong_arch", "wrong_version", "wrong_repository"]:
                changed = copy.deepcopy(manifest)
                artifacts = changed["artifacts"][tool]
                if mutation == "missing_arch":
                    del artifacts["linux-arm64"]
                elif mutation == "wrong_arch":
                    artifacts["linux-arm64"] = artifacts["linux-x64"]
                elif mutation == "wrong_version":
                    changed["versions"][tool.replace("-", "_")] = "0.0.0"
                else:
                    artifacts["linux-x64"]["url"] = artifacts["linux-x64"]["url"].replace("github.com/", "github.com/untrusted/")
                with self.subTest(tool=tool, mutation=mutation), self.assertRaises(ValueError):
                    check_bootstrap.check_optional_tools(changed)

    def test_optional_verification_version_cannot_survive_a_pin_update(self):
        manifest = json.loads((setup.ROOT / "toolchain.json").read_text())
        for tool in ["cairo-coverage", "starknet-devnet"]:
            changed = copy.deepcopy(manifest)
            key = tool.replace("-", "_")
            old = changed["versions"][key]
            changed["versions"][key] = "0.99.0"
            for artifact in changed["artifacts"][tool].values():
                artifact["url"] = artifact["url"].replace(old, "0.99.0")
            with self.subTest(tool=tool), self.assertRaisesRegex(ValueError, "verification version differs"):
                check_bootstrap.check_optional_tools(changed)
            changed["verification"]["optional_tools"][tool]["version"] = "0.99.0"
            check_bootstrap.check_optional_tools(changed)  # Synthetic projection; no release-verification claim.

    def test_optional_components_install_from_verified_cache_on_both_architectures(self):
        for machine, architecture in [("x86_64", "linux-x64"), ("aarch64", "linux-arm64")]:
            with self.subTest(machine=machine), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                cache = root / "cache"
                cache.mkdir()
                manifest = {"versions": {"cairo_coverage": "0.6.1", "starknet_devnet": "0.10.0"}, "artifacts": {}}
                for tool in ["cairo-coverage", "starknet-devnet"]:
                    archive = root / (tool + ".tar.gz")
                    # Match the two official archive layouts without executing fixture code.
                    entry = tarfile.TarInfo("release/bin/" + tool if tool == "cairo-coverage" else tool)
                    content = b"fixture executable"
                    entry.size, entry.mode = len(content), 0o755
                    with tarfile.open(archive, "w:gz") as tar:
                        tar.addfile(entry, io.BytesIO(content))
                    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
                    archive.rename(cache / digest)
                    manifest["artifacts"][tool] = {architecture: {"url": "https://github.com/fixture/unused", "sha256": digest}}
                (root / "toolchain.json").write_text(json.dumps(manifest))
                destination = root / "private"
                calls = []
                def probe(command, environment):
                    executable = Path(command[0])
                    self.assertEqual(executable.parent, destination / "bin")
                    self.assertTrue(executable.is_symlink())
                    self.assertTrue(executable.resolve().is_relative_to(destination / "store"))
                    self.assertEqual(command[1:], ["--version"])
                    self.assertTrue(environment["PATH"].startswith(str(destination / "bin")))
                    calls.append(executable.name)
                    return executable.name + " " + manifest["versions"][executable.name.replace("-", "_")] + "\n"
                argv = ["setup.py", "--components", "cairo-coverage", "starknet-devnet", "--destination", str(destination), "--cache", str(cache)]
                with mock.patch.object(setup, "ROOT", root), mock.patch.object(sys, "argv", argv), mock.patch.object(setup.platform, "system", return_value="Linux"), mock.patch.object(setup.platform, "machine", return_value=machine), mock.patch.object(setup, "probe_version", side_effect=probe), mock.patch.object(setup.urllib.request, "urlopen") as network:
                    setup.main()
                    setup.main()  # Reuse only the same verified archive and managed identity.
                    network.assert_not_called()
                self.assertEqual(calls, ["cairo-coverage", "starknet-devnet"] * 2)
                self.assertEqual({p.name for p in (destination / "bin").iterdir()}, {"cairo-coverage", "starknet-devnet"})


if __name__ == "__main__":
    unittest.main()
