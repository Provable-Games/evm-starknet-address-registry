"""Check that CI exercised retained package and authenticated local release outputs."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def check(deployment_path, package_dir, revision):
    deployment = json.loads(deployment_path.read_text())
    package = json.loads((package_dir / "checked-package.json").read_text())
    for record in (deployment, package["evidence"]):
        source = record["source"]
        if source["revision"] != revision or source["dirty"] is not False:
            raise ValueError("Release record is not bound to the clean CI head")

    if deployment["kind"] != "local-deployment-success" or deployment["environment"] != "local-devnet":
        raise ValueError("Missing local-only deployment success")
    if deployment["server_stopped"] not in {"-15", "-9", "0"}:
        raise ValueError("Owned devnet did not report cleanup")
    readback = deployment["authenticated_readback"]
    if readback["native_version"] != "49" or not readback["block"]["blockHash"]:
        raise ValueError("Missing authenticated readback at a concrete block")
    if len(readback["receipts"]) != 2 or any(receipt["status"] != "succeeded" for receipt in readback["receipts"]):
        raise ValueError("Declaration and deployment receipts must succeed")

    if package["kind"] != "local-checked-sdk-pack":
        raise ValueError("Missing checked SDK package record")
    archive = package["archive"]
    filename = archive["filename"]
    if filename != Path(filename).name or not filename.endswith(".tgz"):
        raise ValueError("Invalid retained archive filename")
    data = (package_dir / filename).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != archive["bytes"] or digest != archive["sha256"] or digest != package["evidence"]["archive_sha256"]:
        raise ValueError("Retained archive differs from the checked bytes")
    print(f"Clean-head local deployment and checked SDK archive verified: {revision}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment", required=True, type=Path)
    parser.add_argument("--package-dir", required=True, type=Path)
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    check(args.deployment, args.package_dir, revision)


if __name__ == "__main__":
    main()
