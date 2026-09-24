import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review_capacity as capacity
import review_ci as ci

SETTINGS = json.loads((ci.ROOT / ".github/review/providers.json").read_text())


class CapacityTests(unittest.TestCase):
    def test_exact_byte_boundary_and_invalid_configuration(self):
        maximum = SETTINGS["maximum_context_bytes"]
        capacity.validate_capacity(SETTINGS)
        capacity.require_context_size(b"x" * maximum, maximum)
        with self.assertRaisesRegex(ValueError, "no content was silently omitted"):
            capacity.require_context_size(b"x" * (maximum + 1), maximum)
        for key, value in [("context_window_tokens", 1050000),
                           ("auto_compact_token_limit", 800000),
                           ("auto_compact_token_limit", True)]:
            invalid = copy.deepcopy(SETTINGS)
            invalid["codex"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                capacity.validate_capacity(invalid)
        for value in [0, True, maximum + 1]:
            with self.assertRaises(ValueError):
                capacity.validate_capacity({**SETTINGS, "maximum_context_bytes": value})

    def test_large_context_preserves_full_snapshot_and_diff_for_unified_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            def git(*args):
                return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false",
                    "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
                    check=True, capture_output=True).stdout.decode().strip()
            git("init")
            (repo / "unchanged.txt").write_text("UNCHANGED_SENTINEL\n")
            git("add", ".")
            git("commit", "-m", "base")
            base = git("rev-parse", "HEAD")
            (repo / "protocol").mkdir()
            text = "BEGIN_SENTINEL\n" + "0123456789abcdef" * 35000 + "\nEND_SENTINEL é\n"
            (repo / "protocol/large.txt").write_text(text)
            git("add", ".")
            git("commit", "-m", "head")
            head = git("rev-parse", "HEAD")
            meta = {"base": base, "head": head}
            output = root / "context"
            expected = ci.prepare_context(repo, meta, output, SETTINGS["maximum_context_bytes"])
            self.assertEqual({item["provider"] for item in expected}, {"codex", "claude"})
            self.assertEqual({item["role"] for item in expected}, {"general"})
            diff = ci.git(repo, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                          "--unified=30", f"{base}...{head}", "--").decode()
            sizes = []
            for path in output.glob("*.txt"):
                prompt = path.read_text()
                sizes.append(len(prompt.encode()))
                self.assertGreater(sizes[-1], 1024 * 1024)
                data = json.loads(prompt.splitlines()[-1])
                self.assertEqual(data["diff"], diff)
                self.assertEqual({f["path"]: f["content"] for f in data["head_files"]},
                                 {"protocol/large.txt": text, "unchanged.txt": "UNCHANGED_SENTINEL\n"})
            self.assertEqual(len(sizes), 1)
            # Count the composed policy+role+JSON bytes, including Unicode escaping.
            ci.prepare_context(repo, meta, root / "exact", max(sizes))
            with self.assertRaisesRegex(ValueError, "no content was silently omitted"):
                ci.prepare_context(repo, meta, root / "oversized", min(sizes) - 1)
            self.assertFalse((root / "oversized/manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
