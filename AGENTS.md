# AI contributor instructions

Read `README.md` and the relevant component guide before editing. For protocol work,
read the normative `protocol/spec.md`, then inspect `protocol/README.md`, the ABI,
vectors, and contract/SDK code. `toolchain.json` pins tool versions.

- Keep the contract and SDK generic. ERC-1271, ERC-6492, messaging, upgrades,
  administrative control, and application policy are outside the current scope.
- Preserve approved signing revision `5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a`:
  its separate link/move schemas, exact statements, label rules, state transitions,
  ABI, and vectors. Get explicit approval before changing the protocol.
- Use a dedicated task branch and worktree based on freshly fetched `origin/main`.
  Do not edit another contributor's worktree. Independent reviewers use separate
  detached worktrees and do not edit the task tree.
- Coordinate shared files with the supervisor. The root npm lockfile and protocol
  ABI/vector artifacts each need one assigned writer. The supervisor owns toolchain
  pins, workflows, and root documentation.
- Run the relevant checks with warnings visible. Never force unsupported
  dependencies, silently change pins, or count an empty test suite as passing.
- For a PR, commit and push, then open the PR. Wait at least 900 seconds after
  each revision before assessing all workflows and review comments. Address
  feedback and merge only when required checks and reviews are complete for the
  latest head.
- Do not expose credentials. Public deployments, package publication, paid
  infrastructure, and organization settings require separate authorization.

When assigned to implementation or independent review, use GPT-6 Astra at medium
reasoning effort. Do not delegate further without a supervisor assignment.
