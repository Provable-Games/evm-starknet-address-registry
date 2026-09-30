# Review configuration

Models and effort are required organization Actions variables exposed to this repository:
`CODEX_REVIEW_MODEL`, `CODEX_REVIEW_EFFORT`, `CLAUDE_REVIEW_MODEL`, and
`CLAUDE_REVIEW_EFFORT`. They control invocation and comment headings; missing or
unsafe values fail before provider execution. Provider JSON retains context limits and credential names, rather than model
defaults. Specialist routing remains in its existing configuration.

`CODEX_CLI_VERSION` selects an exact npm version or `latest` for review runs.
The committed CLI manifests remain available for offline compatibility fixtures.
These custom runners execute Claude directly with isolated configuration and
restricted tools. They retain their locked Claude transport runtime; repositories
using Claude's action instead use its maintained `v1` installer.

Review jobs use `ubuntu-24.04-arm`. Source preparation, completion checks,
publication, and required review gates retain their existing trust boundaries.
