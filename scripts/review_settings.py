"""Resolve the public Actions variables used by the trusted review jobs."""

import re

MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
EFFORT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def review_settings(environment):
    reviewers = {}
    for provider in ("codex", "claude"):
        settings = {}
        for field, pattern in (("model", MODEL), ("effort", EFFORT)):
            name = f"{provider.upper()}_REVIEW_{field.upper()}"
            value = environment.get(name, "")
            if not pattern.fullmatch(value):
                raise ValueError(f"{name} must be a simple identifier in Actions variables accessible to this repository")
            settings[field] = value
        reviewers[provider] = settings
    return reviewers


def offline_review_settings():
    """Explicit fixture for credential-free CLI, transport and unit tests."""
    return review_settings({
        "CODEX_REVIEW_MODEL": "gpt-6-luna", "CODEX_REVIEW_EFFORT": "max",
        "CLAUDE_REVIEW_MODEL": "claude-opus-5-5", "CLAUDE_REVIEW_EFFORT": "medium",
    })
