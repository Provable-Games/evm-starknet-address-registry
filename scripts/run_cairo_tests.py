#!/usr/bin/env python3
"""Run scarb test and reject Foundry's successful-but-empty test selection."""

import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_passing_tests(output):
    plain = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    summaries = re.findall(r"^Tests: (\d+) passed, (\d+) failed, (\d+) ignored, (\d+) filtered out\s*$", plain, re.MULTILINE)
    if not summaries or any(int(failed) for _, failed, _, _ in summaries):
        raise ValueError("Missing or failed Foundry test summary")
    passed = sum(int(passed) for passed, _, _, _ in summaries)
    if passed == 0:
        raise ValueError("Foundry selected no passing tests")
    return passed


def configure_ci_fuzzer_seed():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    seed = os.environ.get("SNFORGE_FUZZER_SEED")
    if seed is None:
        seed = str(secrets.randbelow(2**63 - 1) + 1)
        os.environ["SNFORGE_FUZZER_SEED"] = seed
    memory_dir = os.environ.get("CAIRO_CI_MEMORY_DIR")
    if memory_dir:
        output = Path(memory_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "fuzzer-seed.json").write_text(
            json.dumps({"SNFORGE_FUZZER_SEED": seed}, indent=2) + "\n"
        )
    # Keep wrapper diagnostics separate from the Foundry output stream so
    # callers can capture and validate the test command's output reliably.
    print(f"Foundry fuzzer seed: {seed}", file=sys.stderr, flush=True)


def main():
    configure_ci_fuzzer_seed()
    command = ["scarb", "test"]
    chunks = []
    # Preserve partial diagnostics in CI even if the job is cancelled or times out.
    with subprocess.Popen(command, cwd=ROOT / "contracts", stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            chunks.append(line)
        status = process.wait()
    if status:
        raise subprocess.CalledProcessError(status, command)
    count = require_passing_tests("".join(chunks))
    print(f"Nonempty Foundry suite verified: {count} passing tests.")


if __name__ == "__main__":
    main()
