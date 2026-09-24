# Ethereum address association registry

`EthereumAddressAssociationRegistry` is an immutable Starknet contract class that
maps each Ethereum address to at most one Starknet account. An account can receive
many links. The class has no owner, upgrade path, asset policy, or external account
verifier.

**Mainnet class hash:**
`0x0125d11441d1e4971f3e327474fcd6878ca80c9941017cbacd643383ee227156`.
The class is declared on Starknet Mainnet; each deployed instance has its own
address and state. The [mainnet declaration record](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/deployments/mainnet-class.json)
contains the transaction and class readback. A [Sepolia instance](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/deployments/sepolia.json)
is recorded separately; its [deployment notes](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/deployments/README.md)
link the later lifecycle evidence.

## Interface

| Operation                     | Authorization                                             | Effect                                               |
| ----------------------------- | --------------------------------------------------------- | ---------------------------------------------------- |
| `link`                        | Ethereum EIP-712 signature and destination account caller | Create an association                                |
| `move`                        | Ethereum EIP-712 signature and new destination caller     | Change its destination                               |
| `revoke`                      | Ethereum EIP-712 signature; any account may relay         | Remove an association, if present                    |
| `unlink`                      | Current linked account caller                             | Remove an association                                |
| `invalidate_pending_incoming` | Destination account caller                                | Advance nonce for that account/Ethereum-address pair |

Read methods expose forward and reverse associations, nonces, the signing domain,
and version. Reverse pages have a limit of 1–100; removal can reorder them, so
clients should read all pages at one block. Failed calls leave storage unchanged
and emit no events.

The constructor takes `ethereum_chain_id: u256` and an immutable
`account_label: ByteArray` of 1–48 ASCII bytes. The supported chain pairs are
Ethereum `1` / `SN_MAIN` and Ethereum `11155111` / `SN_SEPOLIA`.
Consumers should authenticate the deployed address, class hash, chain pair, and
label before relying on a link.

The [protocol specification](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/protocol/spec.md)
defines the exact statements, signatures, state transitions, and label grammar.
The [compiler ABI and vectors](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/protocol/README.md)
fix the approved signing revision
`5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a`.

## Local checks

From the repository root, after [setup](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/README.md#setup):

```sh
scarb --manifest-path contracts/Scarb.toml fmt --check
scarb --manifest-path contracts/Scarb.toml lint --test --deny-warnings
scarb --manifest-path contracts/Scarb.toml build
python3 scripts/check_protocol.py
python3 contracts/generate_golden_tests.py --check
python3 contracts/generate_execution_tests.py --check
python3 contracts/test_validation.py
python3 scripts/run_cairo_tests.py
```

The test wrapper rejects an empty Foundry suite. Tests cover the frozen vectors,
authorization and rejection paths, nonce transitions, pagination, and state-model
sequences. The [production inventory](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/contracts/production-inventory.json)
and [resource cases](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/contracts/resource-cases.json)
record the coverage and measurement scope. To collect fresh evidence, use new
output directories:

```sh
python3 scripts/setup.py --components scarb foundry cairo-coverage
python3 contracts/run_evidence.py resources --output .tools/cairo-evidence/resources
python3 contracts/run_evidence.py coverage --output .tools/cairo-evidence/coverage
```
