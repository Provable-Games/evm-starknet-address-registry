# Protocol specification

This is the normative behavior of signing revision
`5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a`. The compiler
[`abi.json`](abi.json) fixes the public interface; independent
[`vectors.json`](vectors.json) fixes serialized examples.

## Scope and identity

The immutable, permissionless Starknet registry maps each Ethereum address to at
most one Starknet account. An account may receive many links. The registry checks
Ethereum secp256k1 key signatures locally and uses the immediate Starknet caller
for account-authorized operations. It has no owner, upgrade, registrar, asset
policy, or backend verifier. A link records key authorization and account
acceptance; it proves neither personal identity nor asset approval. ERC-1271,
ERC-6492, messaging, and contract-wallet policy are outside this revision.

The constructor accepts `ethereum_chain_id: u256` and immutable
`account_label: ByteArray`. The label is 1–48 ASCII bytes matching
`[A-Za-z0-9]+(?: [A-Za-z0-9]+)*`, with case preserved and no normalization.
Only these Ethereum signing / Starknet execution pairs are valid:

| Ethereum chain ID | Starknet chain ID | Technical name |
| --- | --- | --- |
| `1` | ASCII felt `SN_MAIN` | Starknet Mainnet |
| `11155111` | ASCII felt `SN_SEPOLIA` | Starknet Sepolia |

The account chain ID comes from Starknet execution context. The registry address
is its own full `ContractAddress`, below `2^251`. Ethereum addresses are 20 bytes;
Starknet addresses in signed messages are full 32-byte, big-endian `bytes32` words.
Never truncate or reduce an address modulo a field.

## EIP-712 authorization

Domain type and field order:

```text
EIP712Domain(string name,string version,uint256 chainId,bytes32 salt)
```

The domain values are exact:

```text
name: Account Address Association
version: 1
salt_namespace: Account Address Association/v1
```

`chainId` is the configured Ethereum signing chain ID. With `word(x)` denoting
exactly 32 unsigned big-endian bytes, the domain salt is:

```text
keccak256(keccak256(UTF8("Account Address Association/v1")) || word(account_chain_id) || word(registry_address))
```

There is no `verifyingContract` field. The account chain ID and registry address
in the salt bind signatures to the actual deployment. All types, field order,
case, spaces, and punctuation below are exact. `{accountLabel}` is literal
substitution of the immutable label, without braces or a trailing newline.

**LinkAddress** (accepted only by `link`):

```text
LinkAddress(string statement,address ethereumAddress,bytes32 accountAddress,uint256 accountChainId,bytes32 registryAddress,uint256 ethereumNonce,uint256 recipientNonce,uint64 deadline)
Link my Ethereum address to this {accountLabel} account. This does not approve asset transfers.
```

**MoveAddress** (accepted only by `move`):

```text
MoveAddress(string statement,address ethereumAddress,bytes32 accountAddress,bytes32 previousAccountAddress,uint256 accountChainId,bytes32 registryAddress,uint256 ethereumNonce,uint256 recipientNonce,uint64 deadline)
Move my Ethereum address link from the previous {accountLabel} account shown here to this account. This does not approve asset transfers.
```

**RevokeAssociation** (accepted only by `revoke`):

```text
RevokeAssociation(string statement,address ethereumAddress,bytes32 currentAccountAddress,uint256 accountChainId,bytes32 registryAddress,uint256 ethereumNonce,uint64 deadline)
Remove my Ethereum address link to the {accountLabel} account shown here, if any, and cancel requests using the current Ethereum nonce.
```

The signed Ethereum address `E` and destination `S` must be nonzero. A move's
previous account `P` must be nonzero and different from `S`. A revoke signs the
current account, or the zero `bytes32` sentinel when unlinked. The account chain
ID, full registry address, current Ethereum nonce `N(E)`, and destination pair
nonce `R(S,E)` where present must match the authenticated deployment and state.
`deadline` is a nonzero `uint64` Unix timestamp; execution accepts equality with
the block timestamp and rejects later execution. The contract imposes no maximum
window. Expiry affects an unused request, not an existing link.
The SDK proposes a deadline 900 seconds after the current Starknet block time.

Use Ethereum Keccak-256 and `keccak256(0x1901 || domainSeparator ||
hashStruct(message))`; EIP-712 integers use 32-byte big-endian encoding and
strings contribute Keccak hashes. The client requests `eth_signTypedData_v4`,
without personal-sign, text, or digest fallback. Cairo accepts
`Signature { r: u256, s: u256, y_parity: bool }`; `u256` calldata is low 128-bit
limb first. Parse 65-byte `r || s || v` with `v` in `{0,1,27,28}` and ERC-2098
compact signatures. Require `1 <= r < n`, `1 <= s <= n/2`, valid secp256k1
recovery, and recovered address `E` (`n` is the curve order).

## State transitions

All state changes and checked nonce/count increments are atomic; overflow
reverts. `N(E)` and `R(S,E)` start at zero and never reset. An active forward
link appears once in the destination's reverse collection. Removal uses
swap-and-pop and repairs the moved entry's index.

| Operation | Required state and caller | Mapping effect | Nonces advanced |
| --- | --- | --- | --- |
| `link` | `E` unlinked; immediate caller is signed `S` | Add `E → S` | `N(E)`, `R(S,E)` |
| `move` | Current account is signed `P`; immediate caller is signed `S` | Replace `E → P` with `E → S` | `N(E)`, `R(P,E)`, `R(S,E)` |
| `unlink` | Immediate caller is current nonzero account | Remove link | `N(E)`, `R(caller,E)` |
| Signed `revoke` | Signed current account matches state; any caller may relay | Remove link if present | `N(E)`, plus `R(P,E)` if linked |
| `invalidate_pending_incoming(E)` | Nonzero immediate caller `S`, nonzero `E` | None | `R(S,E)` only |

Link and move require valid Ethereum signatures and the destination caller;
unlink and pair cancellation need no Ethereum signature. Revoke requires a
valid signature even when unlinked and always advances `N(E)`. The destination
nonce in link/move is the **new** account's pair nonce. Pair cancellation works
while unlinked and invalidates pending link and move requests using that pair
nonce; it leaves existing links and all other pairs unchanged. A move is never
reinterpreted as a link after the previous account unlinks.

Nonce changes invalidate requests using the old nonce, including after a later
return to the same account. They cannot undo a request that executed first or
guarantee cancellation of deliberately signed future-nonce requests. The SDK
uses current, authenticated nonces and does not offer future-nonce signing.
Mapping changes emit `AssociationChanged` first, then `EthereumNonceAdvanced`,
then `RecipientNonceAdvanced` (old account before new on move). Operation codes
are link `1`, move `2`, unlink `3`, revoke `4`. An unlinked revoke emits only the
Ethereum nonce event; pair cancellation emits only the recipient nonce event.

## Consent and client behavior

Before signing, display full Ethereum and account addresses (both accounts for
a move), actual chains and registry, and the absolute deadline with timezone.
Explain that links are public and persist until removed or moved, while past
transactions remain public and other applications may recognize a link. Distinguish
Ethereum signing from the destination account's Starknet transaction and fee.
The signed English statement above remains exact; explanatory UI may be
translated. Wallet paths that cannot show/sign the required typed data are
unsupported. Authenticate deployment, label, state, and nonces at a consistent
block before signing; recheck and simulate before submission. Treat a dismissed
wallet prompt as local abandonment, not on-chain cancellation. Claim completion
only after successful execution and state readback. Real wallet signing displays
must be verified before advertising support for a wallet path.
