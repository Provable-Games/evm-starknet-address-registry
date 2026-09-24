#!/usr/bin/env python3
"""Install the hash-locked independent oracle in a private, isolated Python venv."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "scripts/reference/wheels.lock.json"


def verify(path, expected):
    with path.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"Wheel SHA-256 mismatch: {path.name}")


def wheel(artifact, cache):
    url = urllib.parse.urlparse(artifact["url"])
    if url.scheme != "https" or url.hostname != "files.pythonhosted.org":
        raise ValueError("Only official PyPI HTTPS wheel artifacts are accepted")
    filename = artifact["filename"]
    if Path(filename).name != filename or not filename.endswith(".whl"):
        raise ValueError("Invalid wheel filename")
    target = cache / artifact["sha256"] / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                with urllib.request.urlopen(artifact["url"], timeout=120) as response:
                    shutil.copyfileobj(response, stream)
                stream.close()
                verify(temporary, artifact["sha256"])
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
    verify(target, artifact["sha256"])
    return target


def environment():
    result = {key: value for key, value in os.environ.items()
              if not key.startswith(("PYTHON", "PIP_"))}
    result.update(PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK="1")
    return result


def validate_lock(lock, manifest, requirements):
    if (lock.get("schema_version") != 1 or lock.get("python") != manifest["versions"]["python"]
            or lock.get("distribution") != manifest["python_distribution"]["release"]):
        raise ValueError("Reference interpreter/distribution lock differs from toolchain")
    if set(lock.get("roots", [])) != {"eth-account", "eth-keys", "eth-hash", "pycryptodome"}:
        raise ValueError("Reference roots differ from the independent oracle agreement")
    packages = lock.get("packages", {})
    if not packages or not set(lock["roots"]).issubset(packages):
        raise ValueError("Reference closure is missing roots")
    lines = ["# Exact independent reference closure; both Linux wheel architectures are hash-locked."]
    for name, package in {"pip": lock["pip"], **packages}.items():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError("Invalid locked package name")
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", package["version"]):
            raise ValueError("Reference package must have an exact stable version")
        if package["metadata_url"] != f"https://pypi.org/pypi/{name}/{package['version']}/json":
            raise ValueError("Reference metadata must identify the exact official PyPI release")
        if set(package["wheels"]) != {"linux-x64", "linux-arm64"}:
            raise ValueError("Reference wheel architectures are incomplete")
        for artifact in package["wheels"].values():
            url = urllib.parse.urlparse(artifact["url"])
            if (url.scheme != "https" or url.hostname != "files.pythonhosted.org"
                    or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"])
                    or Path(artifact["filename"]).name != artifact["filename"]
                    or not artifact["filename"].endswith(".whl")):
                raise ValueError("Reference wheel requires official source, safe filename and SHA-256")
        if name != "pip":
            hashes = sorted({item["sha256"] for item in package["wheels"].values()})
            lines.append(f"{name}=={package['version']} " + " ".join("--hash=sha256:" + value for value in hashes))
    if requirements != "\n".join(lines) + "\n":
        raise ValueError("Reference requirements projection differs from wheel lock")


def create_environment(interpreter, destination, identity, env):
    """Claim an owned empty directory first; build the venv only at its final path.

    The marker records ownership, including interrupted creation/install attempts.
    It does not assert that the environment is complete or safe to skip rebuilding.
    """
    marker = destination / ".registry-reference.json"
    if destination.exists() or destination.is_symlink():
        if (destination.is_symlink() or not destination.is_dir() or marker.is_symlink()
                or not marker.is_file() or json.loads(marker.read_text()).get("format") != 1):
            raise ValueError(f"Refusing to replace unmanaged reference venv: {destination}")
        shutil.rmtree(destination)
    with tempfile.TemporaryDirectory(prefix=".reference-stage-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "owned"
        staged.mkdir()
        (staged / marker.name).write_text(json.dumps(identity, indent=2) + "\n")
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"Refusing to replace unmanaged reference venv: {destination}")
        staged.rename(destination)
    subprocess.run([str(interpreter), "-I", "-m", "venv", str(destination)], env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path, default=ROOT / ".tools")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/reference-wheels")
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    manifest = json.loads((ROOT / "toolchain.json").read_text())
    validate_lock(lock, manifest, (ROOT / "scripts/reference/requirements.lock").read_text())
    architecture = {"x86_64": "linux-x64", "aarch64": "linux-arm64"}.get(platform.machine())
    if platform.system() != "Linux" or architecture is None:
        parser.error("Reference wheels support Linux x64/ARM64 only")
    tools = args.tools.resolve()
    interpreter = tools / "bin/python-reference"
    env = environment()
    reported = subprocess.check_output([str(interpreter), "-I", "-c",
                                        "import platform; print(platform.python_version())"], env=env, text=True).strip()
    if reported != lock["python"]:
        raise ValueError("Private interpreter version differs from lock")
    identity = {"format": 1, "lock_sha256": hashlib.sha256(LOCK.read_bytes()).hexdigest(),
                "interpreter": str(interpreter.resolve()), "architecture": architecture}
    destination = tools / "reference-venv"
    create_environment(interpreter, destination, identity, env)
    python = destination / "bin/python"
    with tempfile.TemporaryDirectory(prefix="registry-wheels-") as temporary:
        wheelhouse = Path(temporary)
        for package in [lock["pip"], *lock["packages"].values()]:
            artifact = package["wheels"][architecture]
            verified = wheel(artifact, args.cache.resolve())
            (wheelhouse / artifact["filename"]).symlink_to(verified)
        pip_lock = wheelhouse / "pip.lock"
        pip_artifact = lock["pip"]["wheels"][architecture]
        pip_lock.write_text(f"pip=={lock['pip']['version']} --hash=sha256:{pip_artifact['sha256']}\n")
        command = [str(python), "-I", "-m", "pip", "--isolated", "install", "--require-hashes",
                   "--only-binary=:all:", "--no-index", "--find-links", str(wheelhouse)]
        subprocess.run([*command, "-r", str(pip_lock)], env=env, check=True)
        subprocess.run([*command, "-r", str(ROOT / "scripts/reference/requirements.lock")], env=env, check=True)
    subprocess.run([str(python), "-I", "-m", "pip", "--isolated", "check"], env=env, check=True)
    subprocess.run([str(python), "-I", "-c",
                    "import sys,site; assert sys.prefix != sys.base_prefix; assert not site.ENABLE_USER_SITE"],
                   env=env, check=True)
    print(f"Independent reference environment: {python}")


if __name__ == "__main__":
    main()
