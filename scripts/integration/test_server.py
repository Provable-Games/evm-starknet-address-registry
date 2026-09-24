"""Exercise cancellation in a real subprocess without running Devnet."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


class CleanupTests(unittest.TestCase):
    def test_sigterm_cleans_only_owned_files_and_reaps_server(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            evidence = directory / 'evidence'
            evidence.mkdir()
            unrelated = directory / 'private-key'
            unrelated.write_text('unrelated fixture')
            script = '''
from pathlib import Path
import sys, time
from server import local_server
p = Path(sys.argv[1])
with local_server([sys.executable, '-c', 'import time; time.sleep(60)'], p) as child:
    (p / 'private-key').write_text('disposable fixture')
    (p / 'accounts.json').write_text('{}')
    (p / 'pid').write_text(str(child.pid))
    time.sleep(60)
'''
            process = subprocess.Popen([sys.executable, '-c', script, str(evidence)],
                                       cwd=Path(__file__).parent)
            try:
                deadline = time.monotonic() + 10
                while not (evidence / 'pid').exists():
                    self.assertIsNone(process.poll())
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.02)
                child = int((evidence / 'pid').read_text())
                process.send_signal(signal.SIGTERM)
                self.assertEqual(process.wait(timeout=20), 143)
                self.assertTrue((evidence / 'server-stopped.txt').exists())
                for name in ['private-key', 'accounts.json', 'server-private.log']:
                    self.assertFalse((evidence / name).exists())
                self.assertEqual(unrelated.read_text(), 'unrelated fixture')
                with self.assertRaises(ProcessLookupError):
                    os.kill(child, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    unittest.main()
