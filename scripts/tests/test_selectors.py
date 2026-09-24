import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_selectors


class SelectorArtifactTests(unittest.TestCase):
    def setUp(self):
        self.abi = json.loads((check_selectors.ROOT / "protocol/abi.json").read_text())
        self.vectors = json.loads((check_selectors.ROOT / "protocol/vectors.json").read_text())

    def test_complete_compiler_and_event_inventory(self):
        cases = check_selectors.selector_cases(self.abi, self.vectors)
        self.assertEqual(len(cases), 17)
        self.assertIn("constructor", cases)
        self.assertIn("RecipientNonceAdvanced", cases)
        check_selectors.check()

    def test_changed_artifact_cannot_keep_stale_cairo_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "protocol").mkdir()
            target = root / check_selectors.TARGET
            target.parent.mkdir(parents=True)
            target.write_text(check_selectors.source(self.abi, self.vectors))
            changed = copy.deepcopy(self.vectors)
            changed["selectors"]["get_version"] = str(int(changed["selectors"]["get_version"]) + 1)
            (root / "protocol/abi.json").write_text(json.dumps(self.abi))
            (root / "protocol/vectors.json").write_text(json.dumps(changed))
            with mock.patch.object(check_selectors, "ROOT", root), self.assertRaisesRegex(ValueError, "differs from frozen artifacts"):
                check_selectors.check()

    def test_call_event_and_inventory_selector_drift_is_rejected(self):
        for change in ["call", "event", "inventory"]:
            vectors = copy.deepcopy(self.vectors)
            if change == "call":
                vectors["vectors"][0]["calldata"]["selector"] = "0"
            elif change == "event":
                vectors["vectors"][0]["expected"]["events"][0]["keys"][0] = "0"
            else:
                del vectors["selectors"]["get_version"]
            with self.subTest(change=change), self.assertRaises(ValueError):
                check_selectors.selector_cases(self.abi, vectors)


if __name__ == "__main__":
    unittest.main()
