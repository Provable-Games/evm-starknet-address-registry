"""Format generated Cairo with pinned Scarb and optionally reject source drift."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def write_generated(destination: Path, text: str):
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='registry-generated-') as temporary:
        project = Path(temporary)
        (project / 'Scarb.toml').write_text('[package]\nname = "generated_fixture"\nversion = "0.1.0"\nedition = "2024_07"\n')
        (project / 'src').mkdir()
        source = project / 'src/lib.cairo'
        source.write_text(text)
        subprocess.run(['scarb', 'fmt', str(source)], check=True, cwd=project)
        formatted = source.read_text()
    if args.check:
        if destination.read_text() != formatted:
            raise SystemExit(f'Stale generated vector test: {destination}')
        print(f'Independent vector inputs match {destination.name}')
    else:
        destination.write_text(formatted)
