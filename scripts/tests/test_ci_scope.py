import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ci_scope
from review_gate import changed_paths

CONFIG = json.loads((ci_scope.ROOT / ".github/ci/scopes.json").read_text())


class ScopeTests(unittest.TestCase):
    def test_shared_inputs_trigger_both_stacks(self):
        for path in ["protocol/abi.json", "protocol/vectors/link.json", "examples/consumer.cairo",
                     "scripts/setup.py", "scripts/integration/run.py", "scripts/integration/starknet-runtime.mjs",
                     "examples/consumer/Scarb.lock", "examples/client/association-preview.ts", ".github/workflows/sdk.yml", "toolchain.json",
                     ".tool-versions", "package.json", "package-lock.json", ".npmrc"]:
            for scope in ["cairo", "sdk"]:
                with self.subTest(path=path, scope=scope):
                    self.assertTrue(ci_scope.selected([path], scope, CONFIG))

    def test_stack_inputs_and_docs_only_changes(self):
        self.assertTrue(ci_scope.selected(["contracts/Scarb.lock"], "cairo", CONFIG))
        self.assertTrue(ci_scope.selected(["packages/sdk/src/client.ts"], "cairo", CONFIG))
        self.assertTrue(ci_scope.selected(["contracts/src/registry.cairo"], "sdk", CONFIG))
        for path in ["packages/sdk/src/index.ts", "tsconfig.json", "eslint.config.mjs", "vitest.config.ts", ".prettierrc.json"]:
            self.assertTrue(ci_scope.selected([path], "sdk", CONFIG))
        for scope in ["cairo", "sdk"]:
            self.assertFalse(ci_scope.selected(["README.md", "AGENTS.md"], scope, CONFIG))
            self.assertFalse(ci_scope.selected([], scope, CONFIG))

    def test_cairo_test_and_evidence_follow_all_relevant_inputs(self):
        for path in ["contracts/Scarb.toml", "protocol/coverage-policy.json", "protocol/vectors/link.json",
                     "toolchain.json", ".tool-versions", ".github/workflows/cairo.yml",
                     ".github/ci/scopes.json", "scripts/ci_scope.py", "scripts/run_cairo_tests.py",
                     "scripts/setup.py", "scripts/check_protocol.py", "scripts/check_selectors.py",
                     "scripts/setup_reference.py", "scripts/reference/generate.py",
                     "scripts/reference/test_oracle.py", "scripts/reference/wheels.lock.json"]:
            with self.subTest(path=path):
                self.assertTrue(ci_scope.needs_cairo_validation([path]))
        for path in ["packages/sdk/src/client.ts", "scripts/review_ci.py", "README.md",
                     "AGENTS.md"]:
            with self.subTest(path=path):
                self.assertFalse(ci_scope.needs_cairo_validation([path]))

    def test_cairo_runner_and_required_gate_skip_unrelated_changes(self):
        workflow = (ci_scope.ROOT / ".github/workflows/cairo.yml").read_text()
        self.assertIn("if: needs.scope.outputs.cairo_validation_changed == 'true'", workflow)
        self.assertIn('test "$TEST_RESULT" = skipped && test "$EVIDENCE_RESULT" = skipped', workflow)

    def test_renaming_out_of_stack_still_runs_checks_and_bad_history_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            def git(*args):
                return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false",
                    "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
                    check=True, capture_output=True, text=True).stdout.strip()
            git("init")
            (repo / "contracts").mkdir()
            (repo / "contracts/old file.cairo").write_text("fixture")
            git("add", ".")
            git("commit", "-m", "base")
            base = git("rev-parse", "HEAD")
            git("mv", "contracts/old file.cairo", "archived.txt")
            git("commit", "-m", "rename")
            head = git("rev-parse", "HEAD")
            paths = changed_paths(repo, base, head)
            self.assertTrue(ci_scope.selected(paths, "cairo", CONFIG))
            with self.assertRaises(subprocess.CalledProcessError):
                changed_paths(repo, "f" * 40, head)

    def test_policy_edits_select_both_stacks_and_reject_invalid_roots(self):
        for scope in ["cairo", "sdk"]:
            self.assertTrue(ci_scope.selected([".github/ci/scopes.json"], scope, CONFIG))
        with self.assertRaises(ValueError):
            ci_scope.selected(["contracts/src/lib.cairo"], "cairo", {**CONFIG, "cairo": ["elsewhere/**"]})

    def test_removing_shared_inputs_cannot_skip_later_changes(self):
        for removed in CONFIG["shared"]:
            config = {**CONFIG, "shared": [path for path in CONFIG["shared"] if path != removed]}
            for scope in ["cairo", "sdk"]:
                with self.subTest(removed=removed, scope=scope), self.assertRaisesRegex(ValueError, "required shared"):
                    ci_scope.selected([removed.replace("**", "fixture")], scope, config)

    def test_invalid_configuration_fails(self):
        with self.assertRaises(ValueError):
            ci_scope.selected([], "unknown", CONFIG)
        with self.assertRaises(ValueError):
            ci_scope.selected([], "cairo", {**CONFIG, "shared": []})


if __name__ == "__main__":
    unittest.main()
