#!/usr/bin/env python3
"""Install manifest-pinned tools into a private directory; never install globally."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
HOSTS = {"github.com", "nodejs.org", "registry.npmjs.org"}


def verify_archive(path, expected):
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path.name}")


def download(artifact, cache):
    url = urllib.parse.urlparse(artifact["url"])
    if url.scheme != "https" or url.hostname not in HOSTS:
        raise ValueError("Tool downloads must use an approved official HTTPS host")
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / artifact["sha256"]
    if target.exists():
        verify_archive(target, artifact["sha256"])
        return target
    with tempfile.NamedTemporaryFile(dir=cache, delete=False) as output:
        temporary = Path(output.name)
        try:
            with urllib.request.urlopen(artifact["url"], timeout=120) as response:
                shutil.copyfileobj(response, output)
            output.close()
            verify_archive(temporary, artifact["sha256"])
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


def extract(archive, destination):
    # data_filter rejects escaping paths/links, devices, and dangerous modes.
    # A private temporary directory prevents partial extraction from becoming active.
    with tarfile.open(archive) as source:
        source.extractall(destination, filter="data")


def install(component, version, artifact, destination, cache):
    archive = download(artifact, cache)
    store = destination / "store"
    store.mkdir(parents=True, exist_ok=True)
    target = store / f"{component}-{version}-{artifact['sha256'][:16]}"
    marker = target / ".registry-tool.json"
    identity = {"component": component, "version": version, "sha256": artifact["sha256"]}
    if target.exists():
        if not marker.is_file() or json.loads(marker.read_text()) != identity:
            raise ValueError(f"Refusing to reuse unmanaged installation: {target}")
        return target
    with tempfile.TemporaryDirectory(dir=store) as temporary:
        unpacked = Path(temporary) / "unpacked"
        unpacked.mkdir()
        extract(archive, unpacked)
        (unpacked / marker.name).write_text(json.dumps(identity) + "\n")
        unpacked.rename(target)
    return target


def expose(binary, link):
    if link.exists() and not link.is_symlink():
        raise ValueError(f"Refusing to overwrite unmanaged executable: {link}")
    temporary = link.with_name(link.name + ".new")
    if temporary.exists() or temporary.is_symlink():
        raise ValueError(f"Another setup may be running: {temporary}")
    temporary.symlink_to(binary)
    temporary.replace(link)


def probe_version(command, environment):
    result = subprocess.run(command, env=environment, check=False, text=True, capture_output=True)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    result.check_returncode()
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / ".tools")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache" / "downloads")
    parser.add_argument("--node-lts", action="store_true")
    parser.add_argument("--components", nargs="+", choices=["node", "npm", "scarb", "usc", "foundry", "actionlint",
                                                           "cairo-coverage", "starknet-devnet", "python"],
                        default=["node", "npm", "scarb", "usc", "foundry", "actionlint"])
    args = parser.parse_args()
    manifest = json.loads((ROOT / "toolchain.json").read_text())
    architecture = {"x86_64": "x64", "aarch64": "arm64"}.get(platform.machine())
    if platform.system() != "Linux" or architecture is None:
        parser.error("Verified setup currently supports Linux x64 and ARM64 only")
    if "npm" in args.components and "node" not in args.components:
        parser.error("npm installation requires node in the same setup command")
    destination, cache = args.destination.resolve(), args.cache.resolve()
    binaries = destination / "bin"
    binaries.mkdir(parents=True, exist_ok=True)
    # Foundry invokes USC at test time; never depend on an unrelated global install.
    if "foundry" in args.components and "usc" not in args.components:
        args.components.append("usc")
    components = [name for name in ["node", "npm", "scarb", "usc", "foundry", "actionlint",
                                   "cairo-coverage", "starknet-devnet", "python"] if name in args.components]
    for component in components:
        key = "node_lts" if component == "node" and args.node_lts else component
        version_key = "starknet_foundry" if component == "foundry" else key.replace("-", "_")
        version = manifest["versions"][version_key]
        artifact = manifest["artifacts"][key]["any" if component == "npm" else f"linux-{architecture}"]
        installed = install(component, version, artifact, destination, cache)
        if component == "npm":
            exports = {"npm": installed / "package/bin/npm-cli.js", "npx": installed / "package/bin/npx-cli.js"}
        elif component == "python":
            exports = {"python-reference": installed / "python/bin/python3.14"}
        elif component in {"actionlint", "starknet-devnet"}:
            exports = {component: installed / component}
        else:
            names = (["snforge", "sncast"] if component == "foundry" else
                     ["universal-sierra-compiler"] if component == "usc" else [component])
            matches = list(installed.glob("*/bin"))
            if len(matches) != 1:
                raise ValueError(f"Unexpected archive layout for {component}")
            # Scarb discovers bundled companion executables beside itself.
            exports = {name: matches[0] / name for name in names}
        for name, source in exports.items():
            if not source.is_file():
                raise ValueError(f"Missing executable in verified archive: {source}")
            expose(source, binaries / name)
        environment = {**os.environ, "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", "")}
        executable = {"foundry": "snforge", "usc": "universal-sierra-compiler", "python": "python-reference"}.get(component, component)
        command = [str(binaries / executable),
                   "-version" if component == "actionlint" else "--version"]
        output = probe_version(command, environment)
        if not output.splitlines() or version not in output.splitlines()[0]:
            raise ValueError(f"Installed {component} did not report expected version {version}")
        if component == "scarb" and f"cairo: {manifest['versions']['cairo']} " not in output:
            raise ValueError("Scarb bundled Cairo version differs from the manifest")
    print(f"Add {binaries} to PATH for this checkout.")


if __name__ == "__main__":
    main()
