#!/usr/bin/env python3
"""Select stack checks and reject known configuration mistakes.

This PR-controlled helper is not a boundary against deliberate helper edits.
"""

import argparse
import fnmatch
import json
import os
from pathlib import Path

from review_gate import changed_paths

ROOT = Path(__file__).resolve().parents[1]

# Keep the Foundry suite and its evidence gates active when any input can alter
# Cairo compilation, test execution, or the gate itself. Unrelated SDK/docs edits
# still skip the expensive Foundry and evidence jobs.
CAIRO_VALIDATION_INPUTS = (
    "contracts/**",
    "protocol/**",
    "toolchain.json",
    ".tool-versions",
    ".github/workflows/cairo.yml",
    ".github/ci/scopes.json",
    "scripts/ci_scope.py",
    "scripts/run_cairo_tests.py",
    "scripts/setup.py",
    "scripts/check_protocol.py",
    "scripts/check_selectors.py",
    "scripts/setup_reference.py",
    "scripts/reference/**",
)


def needs_cairo_validation(paths):
    return any(fnmatch.fnmatchcase(path, pattern)
               for path in paths for pattern in CAIRO_VALIDATION_INPUTS)


def selected(paths, scope, config):
    if scope not in {"cairo", "sdk"} or set(config) != {"shared", "cairo", "sdk"}:
        raise ValueError("Invalid stack scope configuration")
    for patterns in config.values():
        if not isinstance(patterns, list) or not patterns or not all(isinstance(item, str) and item for item in patterns):
            raise ValueError("Scope patterns must be nonempty string lists")
    for name, canonical in [("cairo", "contracts/**"), ("sdk", "packages/**")]:
        if canonical not in config[name]:
            raise ValueError(f"Scope must retain its canonical source root: {name}")
    required_shared = {"protocol/**", "examples/**", "scripts/**", ".github/**", "toolchain.json",
                       ".tool-versions", "package.json",
                       "package-lock.json", ".npmrc"}
    if not required_shared.issubset(config["shared"]):
        raise ValueError("Scope must retain the required shared build and protocol inputs")
    # With this helper unchanged, policy edits exercise every stack for validation.
    if ".github/ci/scopes.json" in paths:
        return True
    return any(fnmatch.fnmatchcase(path, pattern)
               for path in paths for pattern in config["shared"] + config[scope])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope", choices=["cairo", "sdk"])
    args = parser.parse_args()
    config = json.loads((ROOT / ".github/ci/scopes.json").read_text())
    if os.environ["EVENT_NAME"] == "pull_request":
        paths = changed_paths(ROOT, os.environ["BASE_SHA"], os.environ["HEAD_SHA"])
        changed = selected(paths, args.scope, config)
        cairo_validation_changed = needs_cairo_validation(paths)
    else:
        # Main pushes and manual dispatches always run the entire selected stack.
        selected([], args.scope, config)
        changed = True
        cairo_validation_changed = True
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"changed={str(changed).lower()}\n")
        output.write(f"cairo_validation_changed={str(cairo_validation_changed).lower()}\n")
    print(f"{args.scope}: {'run checks' if changed else 'no relevant changed paths'}; "
          f"Cairo tests/evidence needed: {str(cairo_validation_changed).lower()}")


if __name__ == "__main__":
    main()
