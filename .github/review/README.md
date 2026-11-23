# Reviewer configuration

Make these four GitHub Actions configuration variables available to the registry
repository, either directly or through organization variable access.

| Reviewer | Model | Reasoning effort |
| --- | --- | --- |
| Codex | `CODEX_REVIEW_MODEL` | `CODEX_REVIEW_EFFORT` |
| Claude | `CLAUDE_REVIEW_MODEL` | `CLAUDE_REVIEW_EFFORT` |

Choose model and effort identifiers supported by the current reviewer CLIs and
available to the review credentials. The trusted workflow on `main` records the
settings in the review context. Each reviewer invocation and its published heading
use that record, including when only failed jobs rerun. A missing or malformed
variable fails preparation and the `review/required` status.

The trusted workflow resolves the npm `latest` tags for Codex and Claude Code
once during preparation. All reviewer jobs install from the generated lockfile
and report the installed versions before loading credentials. Rerunning only
failed reviewer jobs reuses that lockfile. A fresh workflow run resolves both tags
again. Bootstrap CI checks the CLI arguments, Codex sandbox, and multi-turn
transport without credentials.

Changes to the review workflow take effect after they reach `main`. The
credential-free CLI and synthetic transport checks use explicit test fixtures.
