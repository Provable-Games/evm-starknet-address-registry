#!/usr/bin/env python3
"""Recompile the production registry and enforce the frozen ABI and complete source identity."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULE = "contracts::registry::EthereumAddressAssociationRegistry"
def source_inventory():
    sources = sorted(path.relative_to(ROOT).as_posix()
                     for path in (ROOT / "contracts/src").rglob("*.cairo"))
    if not sources:
        raise ValueError("Production Cairo source inventory is empty")
    return sources + ["contracts/Scarb.toml", "contracts/Scarb.lock"]


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode()


def build(target, test):
    command = [str(ROOT / ".tools/bin/scarb"), "--manifest-path", str(ROOT / "contracts/Scarb.toml"),
               "--target-dir", str(target), "build"]
    if test:
        command += ["--test", "--target-names", "contracts_unittest"]
    subprocess.run(command, check=True)


def production_registry(indexes):
    entries = [(path, entry) for path in indexes
               for entry in json.loads(path.read_text())["contracts"]]
    if len(entries) != 1 or entries[0][1]["module_path"] != MODULE:
        raise ValueError("Expected exactly the registry and no other production contract")
    return entries[0]


def produce():
    manifest = json.loads((ROOT / "toolchain.json").read_text())
    actual = subprocess.check_output([str(ROOT / ".tools/bin/scarb"), "--version"], text=True)
    if (f"scarb {manifest['versions']['scarb']} " not in actual
            or f"cairo: {manifest['versions']['cairo']} " not in actual):
        raise ValueError("Actual compiler differs from frozen provenance")
    with tempfile.TemporaryDirectory(prefix="registry-abi-") as directory:
        target = Path(directory)
        build(target / "production", False)
        production_indexes = list((target / "production").rglob("*.starknet_artifacts.json"))
        if not production_indexes:
            raise ValueError("Fresh production build did not emit an artifact index")
        index, entry = production_registry(production_indexes)
        compiled = json.loads((index.parent / entry["artifacts"]["sierra"]).read_text())
        abi = encoded(compiled["abi"])
        if abi != (ROOT / "protocol/abi.json").read_bytes():
            raise ValueError("Production ABI differs from the frozen agreement; --write cannot replace it")
        if any("ABI_HARNESS_ONLY" in (ROOT / name).read_text() for name in source_inventory()):
            raise ValueError("Constructor-panicking ABI harness remains in production inputs")
        build(target / "test", True)
        test_index = target / "test/dev/contracts_unittest.test.starknet_artifacts.json"
        test_matches = [entry for entry in json.loads(test_index.read_text())["contracts"]
                        if entry["module_path"] == MODULE]
        if len(test_matches) != 1:
            raise ValueError("Expected exactly one registry in test compilation")
        test_compiled = json.loads((test_index.parent / test_matches[0]["artifacts"]["sierra"]).read_text())
        if encoded(test_compiled["abi"]) != abi:
            raise ValueError("Test and production registry ABI differ")
    provenance = {
        "schema_version": 1, "status": "production implementation of the frozen interface",
        "approved_signing_revision": "5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a",
        "module_path": MODULE, "scarb": manifest["versions"]["scarb"],
        "cairo": manifest["versions"]["cairo"], "abi_sha256": hashlib.sha256(abi).hexdigest(),
        "serialization": "UTF-8 JSON, two-space indentation, original compiler array/key order, final LF",
        "sources_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_inventory()},
        "excluded": ["Sierra", "CASM", "class hash", "function indices", "debug metadata", "resource estimates"],
    }
    return {"abi.provenance.json": encoded(provenance)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    from check_selectors import check
    check()
    for name, contents in produce().items():
        destination = ROOT / "protocol" / name
        if args.write:
            destination.write_bytes(contents)
        elif not destination.is_file() or destination.read_bytes() != contents:
            raise ValueError(f"Protocol artifact drift: {name}; inspect and regenerate explicitly")
    print("Frozen ABI, real production registry and complete source provenance verified")


if __name__ == "__main__":
    main()
