"""Private deterministic localhost orchestration. Never connects to a public RPC."""
import json
from contextlib import contextmanager
import hashlib
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from server import local_server

ROOT = Path(__file__).resolve().parents[2]

@contextmanager
def local_deployment(*, registry_only=False, constructor_calldata=None, expected_class_hash=None):
    """Fresh owned devnet; yields private evidence, deployment data and bounded command runner.

    Callers must finish their reads inside the context. This is local test tooling only.
    """
    if constructor_calldata is None:
        constructor_calldata = ["11155111", "0", "0", hex(int.from_bytes(b"Local Registry", "big")), "14"]
    EVIDENCE_PARENT = ROOT / ".tools/integration-evidence"
    EVIDENCE_PARENT.mkdir(parents=True, exist_ok=True)
    EVIDENCE = Path(tempfile.mkdtemp(prefix="run-", dir=EVIDENCE_PARENT))
    EVIDENCE.chmod(0o700)
    commands = []

    def run(args, name, cwd=ROOT, rejection=None):
        commands.append(args)
        (EVIDENCE / "commands.json").write_text(json.dumps(commands, indent=2))
        result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False, timeout=180)
        (EVIDENCE / (name + ".stdout")).write_text(result.stdout)
        (EVIDENCE / (name + ".stderr")).write_text(result.stderr)
        print(name, "exit", result.returncode, flush=True)
        if result.stderr:
            print(result.stderr, end="", flush=True)
        if rejection:
            assert result.returncode != 0, f"{name} unexpectedly succeeded"
            assert rejection in result.stdout + result.stderr, f"{name}: unexpected failure"
            return result.stdout
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect {EVIDENCE}")
        return result.stdout

    def response(output):
        return next(value for line in output.splitlines()
                    if (value := json.loads(line)).get("type") == "response")

    for tool in ["node", "npm", "scarb", "sncast", "universal-sierra-compiler"]:
        run([tool, "--version"], tool + "-version")
    source_files = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT).decode().split("\0")
    (EVIDENCE / "source-hashes.json").write_text(json.dumps({
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in sorted(set(source_files)) if name and (ROOT / name).is_file()
    }, indent=2))
    run(["scarb", "--manifest-path", str(ROOT / "contracts/Scarb.toml"), "build"], "registry-build")
    if not registry_only:
        run(["scarb", "--manifest-path", str(ROOT / "examples/consumer/Scarb.toml"), "build"], "consumer-build")
    compiled_path = ROOT / "contracts/target/dev/contracts_EthereumAddressAssociationRegistry.contract_class.json"
    compiled = json.loads(compiled_path.read_text())
    assert compiled["abi"] == json.loads((ROOT / "protocol/abi.json").read_text())
    (EVIDENCE / "artifact-hashes.json").write_text(json.dumps({
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [compiled_path, ROOT / "protocol/abi.json", ROOT / "package-lock.json",
                     ROOT / "scripts/integration/lifecycle.ts", ROOT / "scripts/integration/transport.ts",
                     ROOT / "examples/consumer/src/lib.cairo"]}, indent=2))
    devnet = shutil.which("starknet-devnet")
    if not devnet:
        raise RuntimeError("Install the manifest-pinned optional starknet-devnet component first")
    assert "0.10.0" in run([devnet, "--version"], "devnet-version")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}/rpc"
    args = [devnet, "--host", "127.0.0.1", "--port", str(port), "--seed", "20260907",
            "--accounts", "3", "--account-class", "cairo1", "--chain-id", "SN_SEPOLIA",
            "--state-archive-capacity", "full"]
    commands.append(args)

    def rpc(method, params=None):
        request = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1,
            "method": method, "params": params or {}}).encode(), headers={"Content-Type": "application/json"})
        value = json.load(urllib.request.urlopen(request, timeout=30))
        if "error" in value:
            raise RuntimeError(value["error"])
        return value["result"]

    with local_server(args, EVIDENCE):
        for attempt in range(100):
            try:
                chain = rpc("starknet_chainId")
                break
            except (OSError, RuntimeError):
                time.sleep(0.1)
        else:
            raise RuntimeError("Devnet startup failed")
        assert int(chain, 16) == int.from_bytes(b"SN_SEPOLIA", "big")
        assert rpc("starknet_specVersion") == "0.10.2"
        account = rpc("devnet_getPredeployedAccounts")[0]
        key = EVIDENCE / "private-key"
        key.write_text(account["private_key"])
        key.chmod(0o600)
        accounts = str(EVIDENCE / "accounts.json")
        run(["sncast", "--accounts-file", accounts, "account", "import", "--name", "integration",
             "--address", account["address"], "--type", "oz", "--private-key-file", str(key),
             "--url", url, "--silent"], "import")
        base = ["sncast", "--accounts-file", accounts, "--account", "integration", "--json", "--wait"]
        deployed = {}
        contracts = [
            ("EthereumAddressAssociationRegistry", ROOT / "contracts", constructor_calldata),
            ("AssociationConsumer", ROOT / "examples/consumer", None),
            ("ConsumerForwarder", ROOT / "examples/consumer", []),
        ]
        for index, (name, cwd, calldata) in enumerate(contracts[:1] if registry_only else contracts):
            declared = response(run(base + ["declare", "--contract-name", name, "--url", url], name + "-declare", cwd))
            if index == 0 and expected_class_hash is not None and int(declared["class_hash"], 16) != int(expected_class_hash, 16):
                raise ValueError("Declared registry class differs from planned compiled class")
            tx = rpc("starknet_getTransactionByHash", {"transaction_hash": declared["transaction_hash"]})
            assert int(tx["version"], 16) == 3
            if calldata is None:
                calldata = [deployed["EthereumAddressAssociationRegistry"]["contract_address"], "2",
                            "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf", "0x123"]
            args = base + ["deploy", "--class-hash", declared["class_hash"], "--salt", str(20260907 + index), "--url", url]
            if calldata:
                args += ["--constructor-calldata", *calldata]
            deployment = response(run(args, name + "-deploy", cwd))
            deployed[name] = {**deployment, "class_hash": declared["class_hash"], "constructor_calldata": calldata,
                              "declare_transaction_hash": declared["transaction_hash"]}
            for transaction_hash in [declared["transaction_hash"], deployment["transaction_hash"]]:
                transaction = rpc("starknet_getTransactionByHash", {"transaction_hash": transaction_hash})
                assert int(transaction["version"], 16) == 3
                receipt = rpc("starknet_getTransactionReceipt", {"transaction_hash": transaction_hash})
                assert receipt["execution_status"] == "SUCCEEDED"
        klass = deployed["EthereumAddressAssociationRegistry"]["class_hash"]
        rejections = [
            ("unsupported-chain-pair", ["1", "0", "0", "0x41", "1"], "AR_BAD_CHAIN_PAIR"),
            ("empty-label", ["11155111", "0", "0", "0", "0"], "AR_BAD_LABEL"),
            ("invalid-label", ["11155111", "0", "0", "0x21", "1"], "AR_BAD_LABEL"),
        ]
        for name, calldata, reason in ([] if registry_only else rejections):
            run(base + ["deploy", "--class-hash", klass, "--salt", "20260999", "--url", url,
                        "--constructor-calldata", *calldata], name, ROOT / "contracts", rejection=reason)
        manifest = {"url": url, "chain_id": chain, "rpc_version": "0.10.2", "seed": 20260907,
                    "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
                    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    "deployed": deployed}
        manifest_path = EVIDENCE / "local-deployments.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        yield EVIDENCE, manifest, run
    print("Evidence:", EVIDENCE, flush=True)


def main():
    with local_deployment() as (evidence, manifest, run):
        run(["node", "scripts/integration/lifecycle.ts", str(evidence / "local-deployments.json")], "lifecycle")


if __name__ == "__main__":
    main()
