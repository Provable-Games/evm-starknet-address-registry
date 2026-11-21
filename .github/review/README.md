# Reviewer configuration

Make these four GitHub Actions configuration variables available to the registry
repository, either directly or through organization variable access.

| Reviewer | Model | Reasoning effort |
| --- | --- | --- |
| Codex | `CODEX_REVIEW_MODEL` | `CODEX_REVIEW_EFFORT` |
| Claude | `CLAUDE_REVIEW_MODEL` | `CLAUDE_REVIEW_EFFORT` |

Choose model and effort identifiers supported by the pinned reviewer CLIs and
available to the review credentials. The trusted workflow on `main` records the
settings in the review context. Each reviewer invocation and its published heading
use that record, including when only failed jobs rerun. A missing or malformed
variable fails preparation and the `review/required` status.

Changes to the review workflow take effect after they reach `main`. The
credential-free CLI and synthetic transport checks use explicit test fixtures.
