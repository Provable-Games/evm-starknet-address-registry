"""Bounded owned-server cleanup on normal exit, SIGINT and SIGTERM."""
from contextlib import contextmanager
from pathlib import Path
import signal
import subprocess


@contextmanager
def local_server(args, evidence: Path):
    server = None
    log = None
    previous = {}

    def interrupted(signum, frame):
        raise SystemExit(128 + signum)

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, interrupted)
        log = (evidence / "server-private.log").open("w")
        Path(log.name).chmod(0o600)
        server = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
        yield server
    finally:
        for signum in previous:
            signal.signal(signum, signal.SIG_IGN)
        try:
            if server is not None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
        finally:
            if log is not None:
                log.close()
            for filename in ["private-key", "accounts.json", "server-private.log"]:
                (evidence / filename).unlink(missing_ok=True)
            if server is not None and server.returncode is not None:
                (evidence / "server-stopped.txt").write_text(str(server.returncode))
            for signum, handler in previous.items():
                signal.signal(signum, handler)
