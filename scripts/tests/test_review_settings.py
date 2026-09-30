import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1]))
from review_settings import configure

class SettingsTests(unittest.TestCase):
    def test_missing_and_unsafe_settings_fail(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError): configure({"codex":{},"claude":{}})
        settings = {"CODEX_REVIEW_MODEL":"model_variant", "CODEX_REVIEW_EFFORT":"high", "CLAUDE_REVIEW_MODEL":"claude-test", "CLAUDE_REVIEW_EFFORT":"medium"}
        with patch.dict(os.environ, settings, clear=True):
            with self.assertRaises(ValueError): configure({"codex":{},"claude":{}})
    def test_org_settings_replace_provider_selection(self):
        settings = {"CODEX_REVIEW_MODEL":"new-model", "CODEX_REVIEW_EFFORT":"high", "CLAUDE_REVIEW_MODEL":"claude-new", "CLAUDE_REVIEW_EFFORT":"high"}
        with patch.dict(os.environ, settings, clear=True):
            result = configure({"codex":{"secret":"credential-name"},"claude":{}})
        self.assertEqual(result["codex"]["model"], "new-model")
        self.assertEqual(result["claude"]["effort"], "high")
        self.assertEqual(result["codex"]["secret"], "credential-name")
