"""Install the manifest-pinned older compiler in a private owned directory."""
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / ".tools/consumer-typescript"
MARKER = ".registry-consumer-typescript-owner"
OWNER = "evm-starknet-address-registry consumer TypeScript installer v1\n"


def claim(destination):
    if destination.is_symlink():
        raise ValueError("Refusing symlink installation destination")
    if destination.exists():
        marker = destination / MARKER
        if marker.is_symlink() or not marker.is_file() or marker.read_text() != OWNER:
            raise ValueError("Refusing unmanaged compiler installation directory")
    else:
        destination.mkdir(parents=True)
        (destination / MARKER).write_text(OWNER)


def verified_members(archive):
    members = archive.getmembers()
    for member in members:
        path = Path(member.name)
        if (path.is_absolute() or ".." in path.parts or not path.parts
                or path.parts[0] != "package" or not (member.isdir() or member.isfile())):
            raise ValueError("Unsafe compiler archive member")
    return members


def verify(data, integrity):
    actual = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    if actual != integrity:
        raise ValueError("Compiler archive integrity mismatch")


def main():
    pin = json.loads((ROOT / "toolchain.json").read_text())["compatibility_consumer_typescript"]
    if pin["version"] != "5.8.3" or pin["url"] != "https://registry.npmjs.org/typescript/-/typescript-5.8.3.tgz":
        raise ValueError("Expected the explicitly reviewed older compiler pin")
    if (ROOT / ".tools").is_symlink():
        raise ValueError("Refusing symlink private tools directory")
    claim(DESTINATION)
    with urllib.request.urlopen(pin["url"], timeout=60) as response:
        if response.url != pin["url"]:
            raise ValueError("Unexpected compiler download redirect")
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError("Compiler archive exceeds bound")
    verify(data, pin["integrity"])
    # A fresh staged extraction prevents following files left by an old install.
    import tempfile
    import shutil
    with tempfile.TemporaryDirectory(prefix="compiler-", dir=DESTINATION) as stage:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            archive.extractall(stage, members=verified_members(archive), filter="data")
        package = Path(stage) / "package"
        assert json.loads((package / "package.json").read_text())["version"] == pin["version"]
        version = subprocess.check_output(["node", str(package / "lib/tsc.js"), "--version"], text=True).strip()
        if version != "Version 5.8.3":
            raise ValueError("Unexpected installed compiler version")
        target = DESTINATION / "package"
        if target.is_symlink():
            raise ValueError("Refusing symlink compiler package")
        if target.exists():
            shutil.rmtree(target)
        package.rename(target)
    (DESTINATION / "installation.json").write_text(json.dumps({**pin, "probe": version}, indent=2))
    print(version, DESTINATION / "package/lib/tsc.js")


if __name__ == "__main__":
    main()
