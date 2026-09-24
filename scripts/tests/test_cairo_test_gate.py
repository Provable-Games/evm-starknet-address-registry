import io
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_cairo_tests as gate


class CairoTestGateTests(unittest.TestCase):
    def test_zero_missing_and_failed_summaries_are_rejected(self):
        for output in ["", "Compiling contracts", "Tests: 0 passed, 0 failed, 0 ignored, 3 filtered out\n",
                       "Tests: 1 passed, 1 failed, 0 ignored, 0 filtered out\n"]:
            with self.subTest(output=output), self.assertRaises(ValueError):
                gate.require_passing_tests(output)

    def test_real_summary_shape_and_colored_output(self):
        output = "Collected 3 test(s) from contracts package\n\x1b[32mTests: 3 passed, 0 failed, 0 ignored, 0 filtered out\x1b[0m\n"
        self.assertEqual(gate.require_passing_tests(output), 3)

    def test_process_failure_cannot_be_overridden_by_partial_passes(self):
        output = "Tests: 1 passed, 0 failed, 0 ignored, 0 filtered out\ncompilation failed\n"
        process = mock.MagicMock()
        process.__enter__.return_value = process
        process.stdout = io.StringIO(output)
        process.wait.return_value = 1
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(gate.os.environ, {"GITHUB_ACTIONS": "true", "SNFORGE_FUZZER_SEED": "123",
                                                   "CAIRO_CI_MEMORY_DIR": directory}):
                with mock.patch.object(gate.subprocess, "Popen", return_value=process), \
                        mock.patch("sys.stdout", new_callable=io.StringIO) as captured, \
                        mock.patch("sys.stderr", new_callable=io.StringIO) as diagnostics:
                    def wait():
                        self.assertEqual(captured.getvalue(), output)
                        return 1
                    process.wait.side_effect = wait
                    with self.assertRaises(subprocess.CalledProcessError):
                        gate.main()
                    self.assertEqual(diagnostics.getvalue(), "Foundry fuzzer seed: 123\n")
            self.assertEqual(json.loads((Path(directory) / "fuzzer-seed.json").read_text()),
                             {"SNFORGE_FUZZER_SEED": "123"})



if __name__ == "__main__":
    unittest.main()
