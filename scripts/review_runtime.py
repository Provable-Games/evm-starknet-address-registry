#!/usr/bin/env python3
"""Run pinned reviewers with isolated configuration and validated final output."""

import argparse
import json
import os
import platform
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

import review_gate as gate
import review_transport as transport
from review_capacity import validate_capacity, require_context_size


ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / ".github/review/runtime/node_modules/.bin"


def codex_native():
    """Locate only the locked Linux native package; never follow package symlinks."""
    architecture = {"x86_64": ("x64", "x86_64"), "aarch64": ("arm64", "aarch64")}.get(platform.machine())
    if platform.system() != "Linux" or architecture is None:
        raise ValueError("Review sandbox requires a supported Linux architecture")
    arch, triple_arch = architecture
    runtime = ROOT / ".github/review/runtime"
    package_key = f"node_modules/@openai/codex-linux-{arch}"
    package = runtime / package_key
    native = package / f"vendor/{triple_arch}-unknown-linux-musl/bin/codex"
    # A fixed path, including every ancestor, must remain inside this trusted install.
    for path in [package / "package.json", native]:
        if path.resolve(strict=True) != path:
            raise ValueError("Codex native package must not redirect outside its fixed install path")
    pin = json.loads((ROOT / "toolchain.json").read_text())["versions"]["codex"]
    expected = pin + "-linux-" + arch
    locked = json.loads((runtime / "package-lock.json").read_text())["packages"][package_key]
    installed = json.loads((package / "package.json").read_text())
    if (locked.get("version") != expected or installed.get("version") != expected
            or installed.get("name") != "@openai/codex"):
        raise ValueError("Codex native package differs from the pinned runtime")
    with native.open("rb") as executable:
        if executable.read(4) != b"\x7fELF" or not os.access(native, os.X_OK):
            raise ValueError("Codex native executable is missing or invalid")
    return native


def codex_config(prepared, private_home):
    # :minimal exposes system binaries/libraries, not the runner's home or checkout.
    # Bubblewrap provides fresh PID/network namespaces and procfs; host /proc is absent.
    settings = json.loads((ROOT / ".github/review/providers.json").read_text())
    validate_capacity(settings)
    return f'''model_context_window = {settings["codex"]["context_window_tokens"]}
model_auto_compact_token_limit = {settings["codex"]["auto_compact_token_limit"]}
model_auto_compact_token_limit_scope = "total"
approval_policy = "never"
default_permissions = "registry_review"
cli_auth_credentials_store = "file"
allow_login_shell = false
web_search = "disabled"
project_doc_max_bytes = 0

[shell_environment_policy]
inherit = "none"

[features]
remote_plugin = false
shell_snapshot = false
skill_mcp_dependency_install = false

[permissions.registry_review.filesystem]
":minimal" = "read"
{json.dumps(str(prepared))} = "read"
{json.dumps(str(codex_native()))} = "read"
{json.dumps(str(private_home))} = "deny"

[permissions.registry_review.network]
enabled = false
'''


def clean_environment():
    # No GitHub Actions tokens, provider credentials, NODE_OPTIONS, or shell hooks.
    return {"PATH": str(ROOT / ".tools/bin") + ":/usr/local/bin:/usr/bin:/bin",
            "HOME": os.environ["HOME"], "LANG": "C.UTF-8", "CI": "true"}


def preflight_codex(prepared, private_home, environment):
    native = codex_native()
    namespaces = {name: os.readlink(f"/proc/self/ns/{name}") for name in ["user", "pid", "net"]}
    canary = private_home / "private-canary"
    canary.write_text("registry-private-preflight-canary")
    link = prepared / "credential-link"
    link.symlink_to(canary)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    test = prepared / "preflight.py"
    test.write_text(f'''from pathlib import Path
import os, socket
assert Path("prompt.txt").is_file(), "prepared context unreadable"
assert Path({str(native)!r}).is_file(), "native Codex executable hidden"
for name, parent in {namespaces!r}.items():
    assert os.readlink("/proc/self/ns/" + name) != parent, name + " namespace not isolated"
try:
    descriptor = os.open({str(native)!r}, os.O_WRONLY)
except OSError:
    pass
else:
    os.close(descriptor)
    raise SystemExit("native executable writable")
try:
    Path({str(ROOT / 'README.md')!r}).read_bytes()
except OSError:
    pass
else:
    raise SystemExit("checkout content exposed")
for path in [{str(canary)!r}, "credential-link", "/proc/{os.getpid()}/root{canary}", "/proc/1/root{canary}"]:
    try:
        Path(path).read_bytes()
    except OSError:
        pass
    else:
        raise SystemExit("private canary readable: " + path)
try:
    Path("/proc/{os.getpid()}/environ").read_bytes()
except OSError:
    pass
else:
    raise SystemExit("host parent environment readable")
try:
    Path({str(private_home / 'forbidden-write')!r}).write_text("x")
except OSError:
    pass
else:
    raise SystemExit("private directory writable")
for host, port in [("127.0.0.1", {port}), ("1.1.1.1", 443)]:
    client = None
    try:
        client = socket.socket()
        client.settimeout(2)
        client.connect((host, port))
    except OSError:
        pass
    else:
        raise SystemExit("network connection unexpectedly succeeded")
    finally:
        if client is not None:
            client.close()
status = Path("/proc/self/status").read_text()
assert "NoNewPrivs:\\t1" in status, "NO_NEW_PRIVS not enabled"
print("Review sandbox canary checks passed.")
''')
    try:
        subprocess.run([str(native), "sandbox", "-C", str(prepared), "-P", "registry_review",
                        "--", "/usr/bin/python3", str(test)], env=environment, check=True, timeout=45)
    finally:
        listener.close()
        link.unlink(missing_ok=True)
        test.unlink(missing_ok=True)
        canary.unlink(missing_ok=True)


def claude_output(stdout):
    result = json.loads(stdout)
    if (not isinstance(result, dict) or result.get("type") != "result"
            or result.get("subtype") != "success" or result.get("is_error") is not False):
        raise ValueError("Claude did not return a successful final result")
    output = (json.dumps(result["structured_output"]) if "structured_output" in result else result.get("result"))
    return json.dumps({"findings": gate.parse_review(output)})


def secret_strings(value):
    if isinstance(value, str):
        return [value] if len(value) >= 8 else []
    if isinstance(value, dict):
        return [secret for item in value.values() for secret in secret_strings(item)]
    if isinstance(value, list):
        return [secret for item in value for secret in secret_strings(item)]
    return []


def redact(text, secrets):
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    return text


def failure_diagnostic(provider, stderr, prompt, secrets):
    # Pinned Codex 0.156.1 event_processor_with_human_output.rs emits
    # ServerNotification::Error / failed turns as eprintln!("ERROR: {}", error).
    # https://github.com/openai/codex/blob/rust-v0.156.1/codex-rs/exec/src/event_processor_with_human_output.rs
    # Remove its echoed input before selection; never log arbitrary transcript tails.
    remaining = stderr.replace(prompt, "") if prompt else stderr
    remaining = redact(remaining, secrets)
    # Rust main() returns anyhow::Result: pre-event request failures use "Error: ".
    errors = ([line for line in remaining.split("\n") if line.startswith(("ERROR: ", "Error: "))]
              if provider == "codex" else [])
    return {"terminal_error": errors[-1][:2000] if errors else "No recognized terminal diagnostic",
            "stderr_bytes": len(stderr.encode()), "stderr_lines": len(stderr.splitlines())}


# Bound diagnostic parsing independently of the complete review context.
CLAUDE_DIAGNOSTIC_BYTES = 64 * 1024
CLAUDE_RESULT_SUBTYPES = frozenset({
    "success", "error_during_execution", "error_max_turns", "error_max_budget_usd",
    "error_max_structured_output_retries",
})


def claude_failure_diagnostic(stdout, stderr):
    # --output-format json reports in-run failures on stdout, including
    # subtype=success/is_error=true with api_error_status (CLI >= 2.1.110).
    # https://code.claude.com/docs/en/headless
    # https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/types.py
    # Emit only fixed enums/booleans and bounded numbers; never error/result text,
    # arbitrary keys, model names, session identifiers, or raw transcript tails.
    diagnostic = {"terminal_error": "No recognized terminal diagnostic",
                  "stdout_bytes": len(stdout.encode()), "stderr_bytes": len(stderr.encode())}
    if diagnostic["stdout_bytes"] > CLAUDE_DIAGNOSTIC_BYTES:
        return diagnostic
    try:
        result = transport.decode_json(stdout)
        if (not isinstance(result, dict) or result.get("type") != "result"
                or not isinstance(result.get("subtype"), str)
                or result["subtype"] not in CLAUDE_RESULT_SUBTYPES
                or type(result.get("is_error")) is not bool):
            return diagnostic
    except (ValueError, TypeError, RecursionError):
        return diagnostic
    diagnostic.update(terminal_error="Claude terminal metadata captured",
                      terminal_subtype=result["subtype"], is_error=result["is_error"])
    status = result.get("api_error_status")
    if type(status) is int and 400 <= status <= 599:
        diagnostic["api_error_status"] = status
    for field in ("duration_ms", "duration_api_ms", "num_turns"):
        value = result.get(field)
        if type(value) is int and 0 <= value <= 2**53 - 1:
            diagnostic[field] = value
    usage = result.get("usage")
    if isinstance(usage, dict):
        for field in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
            value = usage.get(field)
            if type(value) is int and 0 <= value <= 2**53 - 1:
                diagnostic["usage_" + field] = value
    return diagnostic


def json_failure_diagnostic(stdout, stderr, prompt, secrets):
    # Pinned exec_events.rs: ThreadErrorEvent.message and
    # TurnFailedEvent.error.message are structured stdout events; pre-event
    # Rust main failures may still emit the recognized stderr Error: marker.
    # https://github.com/openai/codex/blob/rust-v0.156.1/codex-rs/exec/src/exec_events.rs
    diagnostic = {"terminal_error": "No recognized terminal diagnostic",
                  "stdout_bytes": len(stdout.encode()), "stdout_lines": len(stdout.splitlines()),
                  "stderr_bytes": len(stderr.encode()), "stderr_lines": len(stderr.splitlines())}
    try:
        transport.require(stdout.endswith("\n"), "Incomplete diagnostic stream")
        errors = []
        for line in stdout.split("\n")[:-1]:
            event = transport.decode_json(line)
            transport.fields(event, {"type": str})
            transport.require(event["type"] in {"thread.started", "turn.started", "turn.completed", "turn.failed",
                                                "item.started", "item.updated", "item.completed", "error"},
                              "Unrecognized diagnostic record")
            if event["type"] == "error":
                transport.fields(event, {"message": str})
                errors.append(event["message"])
            elif event["type"] == "turn.failed":
                transport.fields(event.get("error"), {"message": str})
                errors.append(event["error"]["message"])
        if errors:
            message = errors[-1].replace(prompt, "") if prompt else errors[-1]
            diagnostic["terminal_error"] = redact(message, secrets)[:2000]
    except (ValueError, TypeError):
        pass
    if diagnostic["terminal_error"] == "No recognized terminal diagnostic":
        diagnostic.update(failure_diagnostic("codex", stderr, prompt, secrets))
    return diagnostic


def review_command(provider, config, prepared, final):
    if provider == "codex":
        # exec uses default_permissions from the trusted config; -P is sandbox-only.
        return [str(codex_native()), "exec", "--strict-config",
                "--skip-git-repo-check", "--ignore-rules", "--ephemeral", "--color", "never",
                "-m", config[provider]["model"], "-c", f'model_reasoning_effort="{config[provider]["effort"]}"',
                "--output-schema", str(prepared / "schema.json"), "-o", str(final), "-"]
    return [str(BIN / "claude"), "--print", "--safe-mode", "--restricted",
            "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--tools", "", "--disable-slash-commands", "--no-session-persistence",
            "--permission-prompts", "none", "--output-format", "json",
            "--model", config[provider]["model"], "--effort", config[provider]["effort"],
            "--json-schema", (prepared / "schema.json").read_text()]


def check_cli_arguments():
    """Exercise the exact invocation against installed CLIs without a provider request."""
    config = json.loads((ROOT / ".github/review/providers.json").read_text())
    with tempfile.TemporaryDirectory(prefix=".ci-review-", dir=ROOT) as directory:
        private = Path(directory)
        prepared, auth = private / "prepared", private / "auth"
        prepared.mkdir(mode=0o700)
        auth.mkdir(mode=0o700)
        shutil.copyfile(ROOT / ".github/review/result.schema.json", prepared / "schema.json")
        environment = clean_environment()
        environment.update(CODEX_HOME=str(auth), CLAUDE_CONFIG_DIR=str(auth))
        (auth / "config.toml").write_text(codex_config(prepared, auth))
        for provider in ["codex", "claude"]:
            command = review_command(provider, config, prepared, private / "final.json")
            completed = subprocess.run([*command, "--help"], cwd=prepared, env=environment,
                                       capture_output=True, text=True, timeout=30)
            if completed.returncode:
                print(completed.stderr)
                completed.check_returncode()
            print(f"{provider}: pinned CLI accepts review arguments (offline help check).")


def check_sandbox():
    """Run the production profile/canary without loading any provider credentials."""
    with tempfile.TemporaryDirectory(prefix=".ci-review-", dir=ROOT) as directory:
        private = Path(directory)
        prepared, auth = private / "prepared", private / "auth"
        prepared.mkdir(mode=0o700)
        auth.mkdir(mode=0o700)
        (prepared / "prompt.txt").write_text("Credential-free sandbox smoke test")
        (auth / "config.toml").write_text(codex_config(prepared, auth))
        environment = clean_environment()
        environment["CODEX_HOME"] = str(auth)
        preflight_codex(prepared, auth, environment)


def execute(provider, role, context, output, credentials):
    manifest = json.loads((context / "manifest.json").read_text())
    if {"provider": provider, "role": role} not in manifest["expected"]:
        raise ValueError("Reviewer is not in the trusted expected matrix")
    config = json.loads((ROOT / ".github/review/providers.json").read_text())
    identity = {"provider": provider, "role": role, "base": manifest["base"], "head": manifest["head"]}
    record = {**identity, "exit_code": 1, "job_status": "failure", "output": ""}
    output.mkdir(parents=True, exist_ok=True)
    try:
        validate_capacity(config)
        require_context_size((context / f"{role}.txt").read_bytes(), config["maximum_context_bytes"])
        if not credentials:
            print(f"Required credential name: {config[provider]['secret']} (not available)")
            raise ValueError(f"Required credential {config[provider]['secret']} is missing")
        # Outside OS temporary roots: Codex refuses helper aliases under /tmp.
        with tempfile.TemporaryDirectory(prefix=".ci-review-", dir=ROOT) as directory:
            private = Path(directory)
            prepared, auth = private / "prepared", private / "auth"
            prepared.mkdir(mode=0o700)
            auth.mkdir(mode=0o700)
            shutil.copyfile(context / f"{role}.txt", prepared / "prompt.txt")
            shutil.copyfile(ROOT / ".github/review/result.schema.json", prepared / "schema.json")
            environment = clean_environment()
            secrets = [credentials]
            if provider == "codex":
                environment["CODEX_HOME"] = str(auth)
                (auth / "config.toml").write_text(codex_config(prepared, auth))
                # Auth is not written until the exact profile passes its real canary test.
                preflight_codex(prepared, auth, environment)
                session = json.loads(credentials)
                if not isinstance(session, dict) or not isinstance(session.get("tokens"), dict) or not session["tokens"].get("access_token"):
                    raise ValueError("CODEX_AUTH_DOT_JSON must contain the reference OAuth session format")
                secrets += secret_strings(session)
                auth_file = auth / "auth.json"
                auth_file.write_text(credentials)
                auth_file.chmod(0o600)
                final = private / "final.json"
            else:
                environment.update(CLAUDE_CODE_OAUTH_TOKEN=credentials, CLAUDE_CONFIG_DIR=str(auth),
                                   DISABLE_AUTOUPDATER="1", CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
                                   DISABLE_COMPACT="1", DISABLE_AUTO_COMPACT="1")
            command = review_command(provider, config, prepared, private / "final.json")
            prompt = (prepared / "prompt.txt").read_bytes().decode("utf-8", errors="strict")
            def failed(completed, submitted, json_events=False):
                record["exit_code"] = completed.returncode
                print(json.dumps({"provider": provider, "exit_code": completed.returncode,
                                  **(claude_failure_diagnostic(completed.stdout, completed.stderr) if provider == "claude"
                                     else json_failure_diagnostic(completed.stdout, completed.stderr, submitted, secrets) if json_events
                                     else failure_diagnostic(provider, completed.stderr, submitted, secrets))}))
            if provider == "codex" and len(prompt) > transport.NATIVE_CHARS:
                version = json.loads((ROOT / "toolchain.json").read_text())["versions"]["codex"]
                verdict = transport.execute_turns(command, prompt, identity, prepared, auth, environment,
                                                  version, config[provider]["model"], config[provider]["effort"],
                                                  lambda result, submitted: failed(result, submitted, json_events=True))
                normalized = json.dumps({"findings": gate.parse_review(verdict)})
            else:
                if provider == "codex":
                    transport.text_input(prompt)
                completed = subprocess.run(command, input=prompt, cwd=prepared, env=environment,
                                           capture_output=True, text=True, timeout=1200)
                if completed.returncode != 0:
                    failed(completed, prompt)
                    raise ValueError(f"{provider} process failed with exit code {completed.returncode}")
            if provider == "codex" and len(prompt) <= transport.NATIVE_CHARS:
                # Pinned 0.156 human output emits this line for ContextCompaction.
                # Never accept a final verdict after the original context was compacted.
                if "context compacted" in {line.strip() for line in completed.stderr.splitlines()}:
                    raise ValueError("Codex compacted the review context; review is incomplete")
                normalized = json.dumps({"findings": gate.parse_review(final.read_text() if final.is_file() else "")})
            elif provider == "claude":
                normalized = claude_output(completed.stdout)
            record.update(exit_code=0, job_status="success", output=normalized)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        # Do not copy model output, OAuth material, or raw transcripts into artifacts.
        print(f"Review incomplete ({type(error).__name__}). Check credential names, runtime, and sandbox diagnostics.")
    finally:
        (output / "result.json").write_text(json.dumps(record) + "\n")
    return record["job_status"] == "success"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-cli", action="store_true")
    mode.add_argument("--check-sandbox", action="store_true")
    parser.add_argument("--context", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.check_cli:
        check_cli_arguments()
        return
    if args.check_sandbox:
        check_sandbox()
        return
    if args.context is None or args.output is None:
        parser.error("--context and --output are required for a review")
    provider, role = os.environ["REVIEW_PROVIDER"], os.environ["REVIEW_ROLE"]
    if provider not in {"codex", "claude"} or not gate.SLUG.fullmatch(role):
        raise SystemExit("Invalid provider or role")
    # Remove credentials from the environment before any CLI or sandbox subprocess.
    codex = os.environ.pop("CODEX_AUTH_DOT_JSON", "")
    claude = os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", "")
    if not execute(provider, role, args.context, args.output, codex if provider == "codex" else claude):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
