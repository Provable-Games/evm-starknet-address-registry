"""Local-only deployment preparation. No endpoint, key, or public execution options."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/integration"))
from run import local_deployment  # noqa: E402

CONFIG_KEYS = {"schema_version", "environment", "ethereum_chain_id", "account_chain_id", "account_label"}
ARTIFACT = "contracts/target/dev/contracts_EthereumAddressAssociationRegistry.contract_class.json"
WARNING = "LOCAL DEVNET ONLY: disposable software accounts; no public-chain transactions."


def validate_config(value):
    if not isinstance(value, dict) or set(value) != CONFIG_KEYS:
        raise ValueError("Configuration requires exactly the documented fields; external RPC endpoints and keys are forbidden")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("Unsupported configuration schema_version")
    if value["environment"] != "local-devnet":
        raise ValueError("Only a fresh owned loopback local-devnet is supported")
    if value["ethereum_chain_id"] != "11155111" or value["account_chain_id"] != "0x534e5f5345504f4c4941":
        raise ValueError("Local execution requires the exact Ethereum Sepolia / SN_SEPOLIA chain pair")
    label = value["account_label"]
    if not isinstance(label, str) or not 1 <= len(label) <= 48 or re.fullmatch(r"[A-Za-z0-9]+(?: [A-Za-z0-9]+)*", label, flags=re.ASCII) is None:
        raise ValueError("Label must be 1..48 ASCII bytes, alphanumerics separated by single spaces")
    return dict(value)


def constructor(config):
    label = config["account_label"].encode("ascii")
    full, pending = divmod(len(label), 31)
    words = [str(int.from_bytes(label[i * 31:(i + 1) * 31], "big")) for i in range(full)]
    return [config["ethereum_chain_id"], "0", str(full), *words,
            str(int.from_bytes(label[full * 31:], "big")), str(pending)]


def ensure_new(path):
    if os.path.lexists(path):
        raise FileExistsError(f"Refusing existing output (including symlinks): {path}")
    if not path.parent.is_dir():
        raise ValueError("Output parent directory must already exist")


def exclusive_json(path, value):
    """Publish complete JSON atomically without replacing files or dangling symlinks."""
    ensure_new(path)
    encoded = (json.dumps(value, indent=2) + "\n").encode()
    fd, temporary = tempfile.mkstemp(prefix=".local-release-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def command(args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=180, check=False)
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="", flush=True)
    if result.returncode:
        print(result.stdout, file=sys.stderr, end="", flush=True)
        raise RuntimeError(f"Command failed: {args}")
    return result.stdout


def source_identity():
    names = command(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]).split("\0")
    return {
        "revision": command(["git", "rev-parse", "HEAD"]).strip(),
        "dirty": bool(command(["git", "status", "--porcelain"])),
        "sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                   for name in sorted(set(names)) if name and (ROOT / name).is_file()},
    }


def require_pinned_version(tool, reported, pin):
    first_line = reported.splitlines()[0].strip() if reported else ""
    if tool == "node":
        actual = first_line.removeprefix("v") if first_line.startswith("v") else ""
    elif tool == "npm":
        actual = first_line
    else:
        fields = first_line.split(maxsplit=2)
        actual = fields[1] if len(fields) >= 2 and fields[0] == tool else ""
    if actual != pin:
        raise ValueError(f"{tool}: expected manifest pin {pin}, got {reported}")


def prepare(config):
    pins = json.loads((ROOT / "toolchain.json").read_text())["versions"]
    versions = {}
    for tool, pin in [("node", "node"), ("npm", "npm"), ("scarb", "scarb"),
                      ("sncast", "starknet_foundry"), ("universal-sierra-compiler", "usc"),
                      ("starknet-devnet", "starknet_devnet")]:
        version = command([tool, "--version"]).strip()
        require_pinned_version(tool, version, pins[pin])
        versions[tool] = version
    print(command(["scarb", "--manifest-path", str(ROOT / "contracts/Scarb.toml"), "build"]), end="")
    print(command(["npm", "run", "build"]), end="")
    identity = json.loads(command(["node", "scripts/release/identity.ts"]))
    artifacts = [ARTIFACT,
                 "protocol/abi.json", "protocol/abi.provenance.json", "package-lock.json", "toolchain.json"]
    return {
        "schema_version": 1,
        "kind": "local-deployment-plan",
        "environment": "local-devnet",
        "warning": WARNING,
        "config": config,
        "constructor_calldata": constructor(config),
        "identity": identity,
        "artifact_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in artifacts},
        "source": source_identity(),
        "tools": versions,
        "execution": {"host": "127.0.0.1", "port": "fresh ephemeral", "seed": 20260907,
                      "rpc_version": "0.10.2", "account_class": "cairo1", "deployment_salt": "20260907"},
    }


def deploy(plan, output):
    ensure_new(output)
    with local_deployment(registry_only=True, constructor_calldata=plan["constructor_calldata"],
                          expected_class_hash=plan["identity"]["class_hash"]) as (evidence, local, run):
        for name, expected in plan["artifact_sha256"].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"Artifact changed during deployment: {name}")
        request = evidence / "release-readback-request.json"
        request.write_text(json.dumps({"config": plan["config"], "identity": plan["identity"], "local": local}))
        authenticated = json.loads(run(["node", "scripts/release/readback.ts", str(request)], "release-readback"))
        record = {**plan, "kind": "local-deployment-success", "local": local,
                  "authenticated_readback": authenticated, "evidence_directory": str(evidence)}
    # Cleanup must finish before publishing success. The context also cleans up on readback failure.
    record["server_stopped"] = (evidence / "server-stopped.txt").read_text().strip()
    if source_identity() != plan["source"]:
        raise ValueError("Source identity changed during deployment; refusing success record")
    exclusive_json(output, record)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["plan", "deploy-local"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    config = validate_config(json.loads(args.config.read_text()))
    ensure_new(args.output)
    print(WARNING, file=sys.stderr, flush=True)
    plan = prepare(config)
    if args.mode == "plan":
        exclusive_json(args.output, plan)
    else:
        deploy(plan, args.output)
    print(f"{args.mode}: {args.output}")


if __name__ == "__main__":
    main()
