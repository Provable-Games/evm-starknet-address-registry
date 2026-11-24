# Loot Dungeon Safe allowlist adapter

Deploy this read-only contract with the verified address registry and the Ethereum
addresses of the Safes admitted to the pilot. A native L1 link reflects the
Ethereum sender's own authorization policy. Before admitting an address, verify
on Ethereum that a trusted Safe proxy factory deployed the proxy. Check its
current implementation, owners, threshold, enabled modules, guard and fallback
handler against the pilot's approval requirements. Exclude contracts that permit arbitrary outbound
calls by anyone. Also exclude EIP-7702 delegated EOAs, even if they delegate to
Safe code. Their EOA signing key retains independent authority to sign registry
requests. The adapter enforces the configured list, so these checks belong to
the pilot operator.

Send nominations and Starknet acceptances to the upstream registry. Configure
Loot Dungeon's `set_registry_address` with the adapter address. For an admitted
Safe, each `is_associated(ethereum_address, starknet_address)` reads the current
link from the registry. Every other Ethereum address returns false, including
EOAs with valid registry links. This filter applies to the dungeon's
`LinkedAccount` route. Bag ownership is checked separately by the dungeon.

The constructor takes `[registry_address, safe_count, ...safe_addresses]`.
The list and registry address are fixed at deployment. To change either, deploy
another adapter and have the dungeon owner point to it. Record and verify the
class hash and constructor calldata before switching the dungeon pointer.

From this directory, with the repository's pinned tools on PATH, run:

```sh
scarb fmt --check
scarb lint --test --deny-warnings
scarb build
snforge test
```

The Cairo evidence job measures this package separately from the registry. To
reproduce it from the repository root with the pinned tools in `.tools/bin`, run

```sh
python3 contracts/run_evidence.py adapter-coverage --output .tools/cairo-evidence/adapter-coverage
```

The gate reconciles deterministic Foundry traces with
`contracts/production-inventory.json` and requires hits on every mapped
production line and both authored functions. The tests cover invalid constructor
addresses, admitted and unadmitted addresses, and current registry membership.
