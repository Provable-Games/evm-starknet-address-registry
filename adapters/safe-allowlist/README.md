# Loot Dungeon Safe allowlist adapter

Deploy this read-only contract with the verified address registry and the Ethereum
addresses of the Safes admitted to the pilot. Verify the Safe's implementation,
threshold and enabled modules before admitting it. The adapter records addresses;
the Safe controls its own signing policy on Ethereum.

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
