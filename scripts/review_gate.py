#!/usr/bin/env python3
"""Dependency-free routing, review validation, and deterministic comment policy."""

import fnmatch
import html
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


SHA = re.compile(r"[0-9a-f]{40}\Z")
SLUG = re.compile(r"[a-z][a-z0-9-]*\Z")
SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
FIELDS = {"severity", "file", "line", "impact", "trigger", "recommendation"}


def require_sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError("Expected a full Git commit SHA")


def load_config(path):
    config = json.loads(path.read_text())
    providers, roles = config["providers"], config["roles"]
    if providers != ["codex", "claude"] or not roles:
        raise ValueError("Both providers and nonempty roles are required")
    seen = set()
    for role in roles:
        name = role["id"]
        if not SLUG.fullmatch(name) or name in seen:
            raise ValueError("Role IDs must be unique slugs")
        seen.add(name)
        prompt = (path.parent / role["prompt"]).resolve()
        if not prompt.is_relative_to((path.parent / "prompts").resolve()) or not prompt.is_file():
            raise ValueError("Prompt must exist inside the trusted prompts directory")
        if not role["paths"] or not all(isinstance(pattern, str) and pattern for pattern in role["paths"]):
            raise ValueError("Roles need nonempty path patterns")
    if sum(role.get("fallback", False) is True for role in roles) != 1:
        raise ValueError("Exactly one fallback role is required")
    return config


def changed_paths(repo, base, head):
    require_sha(base)
    require_sha(head)
    # Missing history is a subprocess failure, never an empty diff.
    result = subprocess.run(
        ["git", "-C", str(repo), "diff", "--no-ext-diff", "--no-textconv",
         "--no-renames", "--name-only", "-z", f"{base}...{head}", "--"],
        check=True, capture_output=True,
    )
    return [value.decode("utf-8", errors="strict") for value in result.stdout.split(b"\0") if value]


def route(paths, config):
    selected = set()
    fallback = next(role["id"] for role in config["roles"] if role.get("fallback"))
    for path in paths:
        matches = {role["id"] for role in config["roles"]
                   if any(fnmatch.fnmatchcase(path, pattern) for pattern in role["paths"])}
        selected.update(matches or {fallback})
    return [{"provider": provider, "role": role["id"]}
            for provider in config["providers"] for role in config["roles"] if role["id"] in selected]


def parse_review(output):
    if not isinstance(output, str) or not output.strip():
        raise ValueError("Missing final review output")
    if output.strip() == "lgtm":
        return []
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result
    value = json.loads(output, object_pairs_hook=unique_object)
    if not isinstance(value, dict) or set(value) != {"findings"} or not isinstance(value["findings"], list):
        raise ValueError("Expected only a findings array")
    for finding in value["findings"]:
        if not isinstance(finding, dict) or set(finding) != FIELDS:
            raise ValueError("Missing or unexpected finding fields")
        if finding["severity"] not in SEVERITIES:
            raise ValueError("Unknown severity")
        if type(finding["line"]) is not int or finding["line"] < 1:
            raise ValueError("Finding line must be a positive integer")
        for key in FIELDS - {"line"}:
            if not isinstance(finding[key], str) or not finding[key].strip() or len(finding[key]) > 8000:
                raise ValueError("Finding fields must be nonempty bounded text")
        path = PurePosixPath(finding["file"])
        if path.is_absolute() or ".." in path.parts or "\x00" in str(path) or str(path) == ".":
            raise ValueError("Finding path must remain inside the repository")
    return value["findings"]


def assess(expected, results, base, head, *, routing_succeeded):
    require_sha(base)
    require_sha(head)
    errors, findings = [], []
    if not routing_succeeded:
        errors.append("Routing did not complete")
    wanted = {(item["provider"], item["role"]) for item in expected}
    if len(wanted) != len(expected):
        errors.append("Duplicate expected reviewers")
    received = set()
    for result in results:
        key = (result.get("provider"), result.get("role"))
        if key not in wanted or key in received:
            errors.append(f"Unexpected or duplicate reviewer: {key}")
            continue
        received.add(key)
        if result.get("base") != base or result.get("head") != head:
            errors.append(f"Stale review: {key}")
            continue
        # These are trusted executor/job facts, never fields accepted from model output.
        if result.get("job_status") != "success" or type(result.get("exit_code")) is not int or result["exit_code"] != 0:
            errors.append(f"Review execution incomplete: {key}")
            continue
        try:
            parsed = parse_review(result.get("output"))
        except (ValueError, TypeError) as error:
            errors.append(f"Invalid review from {key}: {error}")
            continue
        findings.extend({"provider": key[0], "role": key[1], **finding} for finding in parsed)
    if received != wanted:
        errors.append("Required reviewers are missing")
    blocking = [finding for finding in findings if finding["severity"] in {"CRITICAL", "HIGH"}]
    return {"passed": not errors and not blocking, "errors": errors, "findings": findings}


def markdown_text(value):
    """Render untrusted finding text as wrapping Markdown without active markup."""
    value = re.sub(r"\s+", " ", value).strip()
    value = html.escape(value, quote=False).replace("\\", "\\\\")
    value = re.sub(r"([`*_\[\]|~#-])", r"\\\1", value)
    value = value.replace("@", "&#64;").replace("://", "&#58;//").replace("www.", "www&#46;")
    return re.sub(r"(?m)^([ \t]*)(#{1,6}|[+-]|\d+[.)])(?=\s|$)", r"\1\\\2", value)


def comment_body(provider, role, base, head, findings, *, repository, model, effort,
                 run_id, incomplete=False):
    if provider not in {"codex", "claude"} or not SLUG.fullmatch(role):
        raise ValueError("Invalid reviewer identity")
    if (not isinstance(repository, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            or not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9.-]+", model)
            or not isinstance(effort, str) or not re.fullmatch(r"[a-z]+", effort)
            or not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9-]+", run_id)):
        raise ValueError("Invalid review heading or run identity")
    require_sha(base)
    require_sha(head)
    # Round-trip validation ensures the renderer and gate share the same records.
    parse_review(json.dumps({"findings": findings}))
    # Normal paragraphs wrap long findings; escaping prevents active reviewer markup.
    visible = ("Review incomplete: execution or output validation failed. See the workflow run."
               if incomplete else "lgtm") if not findings else "\n\n".join(
        f"### {finding['severity']} — {markdown_text(finding['file'])}:{finding['line']}\n\n"
        f"**Impact:** {markdown_text(finding['impact'])}\n\n"
        f"**Trigger:** {markdown_text(finding['trigger'])}\n\n"
        f"**Recommended action:** {markdown_text(finding['recommendation'])}" for finding in findings
    )
    heading = f"## {model}-{effort} Code Review: [{head[:7]}](https://github.com/{repository}/commit/{head})"
    return (heading + "\n\n" + visible
            + f"\n\n<!-- registry-review:{provider}:{role}:run:{run_id} -->"
            + f"\n<!-- base:{base} head:{head} -->")


def publication_action(comments, bot_id, provider, role, base, head, current_base, current_head,
                       findings, *, repository, model, effort, run_id, incomplete=False):
    # The publisher must fetch the current PR identity immediately before this decision.
    if (base, head) != (current_base, current_head):
        raise ValueError("Refusing to publish a stale review")
    body = comment_body(provider, role, base, head, findings,
                        repository=repository, model=model, effort=effort,
                        run_id=run_id, incomplete=incomplete)
    marker = f"<!-- registry-review:{provider}:{role}:run:{run_id} -->"
    matching = [comment for comment in comments
                if comment["user"]["id"] == bot_id and marker in comment["body"]]
    if len(matching) > 1:
        raise ValueError("Duplicate bot review comments require reconciliation")
    if matching and matching[0]["body"] != body:
        raise ValueError("Existing review comment differs from this run's result")
    return {"method": "SKIP" if matching else "POST", "body": body}
