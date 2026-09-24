# Protocol agreement

The contract and SDK implement signing revision
`5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a`.
[spec.md](spec.md) is the normative source for signed statements, authorization,
and state transitions. The files here fix the contract/SDK agreement:

| Artifact                                           | Purpose                                                  |
| -------------------------------------------------- | -------------------------------------------------------- |
| [abi.json](abi.json)                               | Complete Cairo 2.20.0 / Scarb 2.20.1 compiler ABI        |
| [abi.provenance.json](abi.provenance.json)         | ABI SHA-256 and source provenance                        |
| [vectors.json](vectors.json)                       | Independent signing, calldata, event, and state examples |
| [vectors.provenance.json](vectors.provenance.json) | Reference generator and dependency identity              |
| [coverage-policy.json](coverage-policy.json)       | Contract and SDK coverage/resource policy                |

The ABI SHA-256 identifies the JSON artifact. It is distinct from a Starknet
class hash and an Ethereum Keccak digest. Generated Sierra and executable
artifacts are not committed. A [Sepolia deployment](../deployments/sepolia.json)
is recorded separately.

## Wire format and reads

The production class is `contracts::registry::EthereumAddressAssociationRegistry`;
public types are in `contracts::interface`. Its constructor takes
`ethereum_chain_id: u256` and `account_label: ByteArray`. `u256` calldata uses
the low 128-bit limb first. Link requests serialize to 7 felts plus 5 signature
felts, move to 8 + 5, and revoke to 5 + 5. Signature parity is exactly 0 or 1.

`get_signing_domain` returns the complete deployment-specific domain and signed
statements. ByteArray values serialize as `[full_word_count, ...full_words,
pending_word, pending_byte_count]`. Each full word holds 31 bytes;
`pending_byte_count` is the number of bytes in the pending word (0–30). Events
have one variant selector key, then their declared keys:

| Event                  | Additional keys           | Data                                        |
| ---------------------- | ------------------------- | ------------------------------------------- |
| AssociationChanged     | Ethereum address          | Previous account, new account, operation u8 |
| EthereumNonceAdvanced  | Ethereum address          | New nonce low, high                         |
| RecipientNonceAdvanced | Account, Ethereum address | New nonce low, high                         |

Operation values are link 1, move 2, unlink 3, and signed revoke 4. Mapping
changes emit first, then Ethereum nonce, then recipient nonces (old before new on
a move). An unlinked revoke emits only the Ethereum nonce event; pending-consent
cancellation emits only the recipient nonce event.

Reverse page limits are 1–100, even for empty results. Removal can reorder the
reverse collection, so clients should pin all pages to one block. Zero-key reads
return zero or empty values as defined in the ABI and specification.

## Application revert identifiers

These ASCII felt values identify registry validation failures. Native decoding,
syscall, and provider failures retain their own diagnostics.

| Identifier              | Meaning                                          |
| ----------------------- | ------------------------------------------------ |
| AR_BAD_LABEL            | Invalid immutable label                          |
| AR_BAD_CHAIN_PAIR       | Unsupported chain pair                           |
| AR_ZERO_ADDRESS         | Required address is zero                         |
| AR_BAD_CALLER           | Immediate caller is unauthorized                 |
| AR_ALREADY_LINKED       | Ethereum address already linked                  |
| AR_NOT_LINKED           | Required association absent                      |
| AR_BAD_PREVIOUS_ACCOUNT | Signed move source differs from storage          |
| AR_BAD_CURRENT_ACCOUNT  | Signed revoke account differs from storage       |
| AR_SAME_ACCOUNT         | Move source equals destination                   |
| AR_STALE_ETH_NONCE      | Ethereum nonce differs from storage              |
| AR_STALE_RECIP_NONCE    | Account/Ethereum pair nonce differs from storage |
| AR_BAD_DEADLINE         | Deadline is invalid                              |
| AR_EXPIRED              | Block time exceeds the inclusive deadline        |
| AR_BAD_SIGNATURE        | Signature or recovered signer is invalid         |
| AR_NONCE_OVERFLOW       | Checked nonce increment overflowed               |
| AR_COUNT_OVERFLOW       | Checked reverse-count increment overflowed       |
| AR_BAD_PAGE_LIMIT       | Page limit is outside 1–100                      |

## Independent verification

The vectors contain 13 signed cases, four unsigned transitions, and seven
constructor/discovery encodings across the supported chains and label boundaries.
The isolated Python oracle does not import the contract or SDK hashing code. Its
addresses and public scalar 1 are test fixtures, not funded wallets.

From the repository root, after [setup](../README.md#setup):

```sh
python3 scripts/setup.py --components scarb foundry python
python3 scripts/setup_reference.py
python3 scripts/check_protocol.py
.tools/reference-venv/bin/python -I scripts/reference/generate.py
.tools/reference-venv/bin/python -I scripts/reference/test_oracle.py
```

`check_protocol.py` rebuilds the frozen ABI, checks source provenance, and checks
the vector-derived selector test. The reference commands check vector
reproducibility. The [contract guide](../contracts/README.md) and
[SDK guide](../packages/sdk/README.md) give the runtime checks. Consumers should
supply a trusted deployment tuple and authenticate its class, chain, label, and
signing domain at a concrete block before requesting a signature.
