#!/usr/bin/env python3
"""Check the committed toolchain projection and trusted review configuration."""

import json
from pathlib import Path
import re
import tomllib
import urllib.parse

from review_gate import load_config


ROOT = Path(__file__).resolve().parents[1]


def check_optional_tools(manifest):
    for tool, repository in [("cairo-coverage", "software-mansion/cairo-coverage"),
                             ("starknet-devnet", "starknet-io/starknet-devnet")]:
        version = manifest["versions"].get(tool.replace("-", "_"))
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError(f"Optional tool requires an exact stable version: {tool}")
        evidence = manifest.get("verification", {}).get("optional_tools", {}).get(tool, {})
        if evidence.get("version") != version:
            raise ValueError(f"Optional tool verification version differs from its pin: {tool}")
        artifacts = manifest["artifacts"].get(tool, {})
        if set(artifacts) != {"linux-x64", "linux-arm64"}:
            raise ValueError(f"Optional tool requires both Linux architectures: {tool}")
        for platform, arch in [("linux-x64", "x86_64"), ("linux-arm64", "aarch64")]:
            prefix = f"{tool}-v{version}" if tool == "cairo-coverage" else tool
            expected = (f"https://github.com/{repository}/releases/download/v{version}/"
                        f"{prefix}-{arch}-unknown-linux-gnu.tar.gz")
            if artifacts[platform].get("url") != expected:
                raise ValueError(f"Optional tool artifact differs from its official release: {tool}/{platform}")


def check_stack_pins(manifest):
    versions = manifest["versions"]
    root_package = ROOT / "package.json"
    if root_package.is_file():
        package = json.loads(root_package.read_text())
        if package.get("workspaces") != ["packages/sdk"]:
            raise ValueError("Workspace inventory changed; coordinate its pin validation before adding workspaces")
        if not (ROOT / "package-lock.json").is_file() or not (ROOT / "packages/sdk/package.json").is_file():
            raise ValueError("Node scaffold requires its root lockfile and SDK manifest")
        lock = json.loads((ROOT / "package-lock.json").read_text())
        # Manifest entries may be reserved before installation. Once any root-lock
        # resolution exists (including a transitive/nested one), enforce its pin.
        for name, pin in manifest["packages"].items():
            suffix = "node_modules/" + name
            for key, entry in lock["packages"].items():
                if key == suffix or key.endswith("/" + suffix):
                    if entry.get("version") != pin["version"] or entry.get("integrity") != pin["integrity"]:
                        raise ValueError(f"Node lock differs from the verified pin: {key}")
        if package.get("packageManager") != "npm@" + versions["npm"]:
            raise ValueError("Root package manager differs from toolchain.json")
        expected_engines = {"node": f"^{versions['node_lts']} || ^{versions['node']}", "npm": versions["npm"]}
        if package.get("engines") != expected_engines or lock["packages"][""].get("engines") != expected_engines:
            raise ValueError("Root runtime constraints differ from approved primary/LTS pins")
        if package.get("private") is not True:
            raise ValueError("Root workspace must remain private")
        sdk_package = json.loads((ROOT / "packages/sdk/package.json").read_text())
        if sdk_package.get("private", False) is not False:
            raise ValueError("SDK package must be publishable")
        for data in [package, sdk_package]:
            # Public peer ranges require an explicit, tested compatibility policy.
            # The SDK has no peers; do not permit unverified ranges.
            for category in ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"]:
                for name, version in data.get(category, {}).items():
                    pin = manifest["packages"].get(name)
                    if pin is None or version != pin["version"]:
                        raise ValueError(f"Unapproved direct Node dependency: {name}@{version}")
                    keys = ["node_modules/" + name]
                    nested = "packages/sdk/node_modules/" + name
                    if nested in lock["packages"]:
                        keys.append(nested)
                    for key in keys:
                        entry = lock["packages"].get(key, {})
                        if entry.get("version") != version or entry.get("integrity") != pin["integrity"]:
                            raise ValueError(f"Node lock differs from the verified pin: {key}")
    cairo_package = ROOT / "contracts/Scarb.toml"
    if cairo_package.is_file():
        cairo_pins = manifest.get("cairo_packages")
        if not isinstance(cairo_pins, dict) or not cairo_pins:
            raise ValueError("Cairo scaffold requires verified cairo_packages pins in toolchain.json")
        for name, pin in cairo_pins.items():
            if (not isinstance(pin, dict) or not isinstance(pin.get("version"), str)
                    or not re.fullmatch(r"\d+\.\d+\.\d+", pin["version"])
                    or pin.get("registry") != "https://scarbs.xyz/"
                    or not isinstance(pin.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", pin["sha256"])):
                raise ValueError(f"Invalid cairo_packages pin: {name}; require exact stable version, https://scarbs.xyz/ registry, and 64-character SHA-256")
        if not (ROOT / "contracts/Scarb.lock").is_file():
            raise ValueError("Cairo scaffold requires its committed Scarb.lock")
        package = tomllib.loads(cairo_package.read_text())
        lock = tomllib.loads((ROOT / "contracts/Scarb.lock").read_text())
        if (package.get("package", {}).get("cairo-version") != "=" + versions["cairo"]
                or package.get("dependencies", {}).get("starknet") != "=" + versions["cairo"]
                or package.get("dev-dependencies", {}).get("snforge_std") != "=" + versions["starknet_foundry"]):
            raise ValueError("Cairo compiler/dependency constraints differ from toolchain.json")
        if package.get("cairo", {}).get("allow-warnings") is not False:
            raise ValueError("Cairo compiler warnings must be fatal")
        if package.get("scripts", {}).get("test") != "snforge test":
            raise ValueError("Cairo test script must be exactly snforge test")
        fuzz = package.get("tool", {}).get("snforge", {})
        if fuzz.get("fuzzer_runs") != 256 or "fuzzer_seed" in fuzz:
            raise ValueError("Cairo fuzz settings must use 256 runs and leave seed selection to CI")
        for entry in lock["package"]:
            if entry.get("name") == package.get("package", {}).get("name") and "source" not in entry:
                continue
            pin = cairo_pins.get(entry.get("name"))
            if (pin is None or entry.get("version") != pin["version"]
                    or entry.get("source") != "registry+" + pin["registry"]
                    or entry.get("checksum") != "sha256:" + pin["sha256"]):
                raise ValueError(f"Unapproved Cairo lock entry: {entry.get('name')}")


def main():
    manifest = json.loads((ROOT / "toolchain.json").read_text())
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported toolchain schema")
    for version in manifest["versions"].values():
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError("Tool versions must be exact stable versions")
    versions = manifest["versions"]
    expected = (f"nodejs {versions['node']}\nscarb {versions['scarb']}\n"
                f"starknet-foundry {versions['starknet_foundry']}\n"
                f"universal-sierra-compiler {versions['usc']}\n")
    if (ROOT / ".tool-versions").read_text() != expected:
        raise ValueError(".tool-versions differs from toolchain.json")
    check_optional_tools(manifest)
    for platforms in manifest["artifacts"].values():
        if set(platforms) not in ({"any"}, {"linux-x64", "linux-arm64"}):
            raise ValueError("Artifact architectures are incomplete")
        for artifact in platforms.values():
            url = urllib.parse.urlparse(artifact["url"])
            if url.scheme != "https" or url.hostname not in {"github.com", "nodejs.org", "registry.npmjs.org"}:
                raise ValueError("Artifact source is not an approved official HTTPS host")
            if not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
                raise ValueError("Artifact requires a SHA-256 digest")
    for action in manifest["actions"].values():
        if not re.fullmatch(r"[0-9a-f]{40}", action["sha"]):
            raise ValueError("Action requires a full commit SHA")
    for package in manifest["packages"].values():
        if not re.fullmatch(r"\d+\.\d+\.\d+", package["version"]):
            raise ValueError("Package requires an exact stable version")
        if not package["integrity"].startswith("sha512-"):
            raise ValueError("Package metadata requires SHA-512 integrity")
    load_config(ROOT / ".github/review/agents.json")
    runtime = json.loads((ROOT / ".github/review/runtime/package.json").read_text())
    lock = json.loads((ROOT / ".github/review/runtime/package-lock.json").read_text())
    expected_dependencies = {"@openai/codex": versions["codex"], "@anthropic-ai/claude-code": versions["claude"]}
    if runtime["dependencies"] != expected_dependencies or lock["packages"][""]["dependencies"] != expected_dependencies:
        raise ValueError("Review CLI dependencies differ from authoritative pins")
    for name, version in expected_dependencies.items():
        if lock["packages"]["node_modules/" + name]["version"] != version:
            raise ValueError("Review CLI lockfile has a different version")
    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        for repository, sha in re.findall(r"uses: ([\w/-]+)@([\w.-]+)", workflow.read_text()):
            action = repository.removesuffix("/restore").removesuffix("/save")
            if action not in manifest["actions"] or manifest["actions"][action]["sha"] != sha:
                raise ValueError(f"Workflow action pin differs from manifest: {repository}@{sha}")
    check_stack_pins(manifest)
    from setup_reference import validate_lock
    validate_lock(json.loads((ROOT / "scripts/reference/wheels.lock.json").read_text()), manifest,
                  (ROOT / "scripts/reference/requirements.lock").read_text())
    print("Toolchain manifest, stack pins, version projection, and review configuration passed.")


if __name__ == "__main__":
    main()
