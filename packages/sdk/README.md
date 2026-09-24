# Address registry SDK

Framework-independent ESM SDK for signing revision
`5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a`. It authenticates registry reads,
prepares link, move, and revoke requests, signs with a selected Ethereum provider,
and can simulate, submit, and read back Starknet transactions through application
adapters.

## Install

```sh
npm install @provable-games/evm-starknet-address-registry
```

The application supplies a reviewed `TrustedDeployment`, a `RegistryTransport`, an
`AccountAdapter`, and the selected EIP-1193 provider. The SDK does not discover
wallets, choose a registry, manage session policy, or set application eligibility.
See the [client example](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/examples/client/README.md) and
[public types](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/packages/sdk/src/protocol.ts).

## Basic flow

```ts
import {
  createRegistryClient,
  createRegistryReader,
} from '@provable-games/evm-starknet-address-registry';

// The host application supplies and reviews these values and adapters.
const reader = createRegistryReader(trustedDeployment, registryTransport);
const client = createRegistryClient({
  deployment: trustedDeployment,
  reader,
  account: accountAdapter,
});
const prepared = await client.prepareLink(ethereumAddress);
// Show both full addresses, the authenticated network and label, the deadline,
// and the public, persistent effect before opening the wallet prompt.
const signed = await client.sign(prepared, selectedEthereumProvider);
const result = await client.submit([signed]);
```

`prepareMove` and `prepareRevoke` use the same signing flow. `encode` returns a
call for an application-owned multicall. `buildUnlinkCall` and
`buildInvalidatePendingIncomingCall` create unsigned calls. Convenience methods
`unlink` and `invalidatePendingIncoming` simulate and submit those operations.
Ethereum-authorized revocation can be signed without access to the linked account;
submission still needs a funded Starknet relay account.

## Trust and reads

`TrustedDeployment` binds both chains, the full registry address, expected class
hash, immutable label, protocol revision, and ABI SHA-256. Each reader query checks
the actual chain, class, signing domain, and contract version at a concrete block.
The application remains responsible for choosing a trustworthy RPC and deployment.

`listAllEthereumAddresses(accountAddress, blockHash, options?)` fetches complete,
unique reverse pages at one block and rejects failed or inconsistent reads. Its
`maxAddresses` client budget defaults to 10,000; callers may choose a different
u64 budget. `compareLinkedAddresses(snapshot, allowed)` computes an intersection
without RPC or an eligibility decision.

Internal Ethereum addresses are lowercase 20-byte hex; account addresses and
hashes use full 32-byte words with context-specific range checks. Numeric values
are `bigint`. The exported address aliases are structural TypeScript types, so
untrusted values still require runtime validation. The
[protocol specification](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/protocol/spec.md) defines exact signed fields,
statements, and calldata.

## Signing and submission

The SDK requests `eth_signTypedData_v4` from the injected provider. It accepts
65-byte v0/1/27/28 and ERC-2098 signatures, checks low-s and recovered signer,
and offers no personal-sign fallback. Prepared requests use current authenticated
nonces and default to a deadline 900 seconds after the observed block time.

A mutable `AccountAdapter` must synchronously increment `generation()` and notify
`subscribeChange` listeners on every account, chain, or disconnect transition.
Changes cancel pending work before execution. Once `execute` returns a transaction
hash, the SDK continues tracking that transaction even if the account changes.

`submit` reauthenticates state and identity, simulates, executes, waits for a
receipt, and reads state at the receipt block. A successful receipt is retained
even when readback is `mismatch` or `unavailable`; either outcome needs inspection
before presenting a currently active association. If a submitted hash is known
but confirmation is inconclusive, the error is `confirmation-unavailable` with
that hash. Reconcile it before attempting another transaction.

## Local checks

After the [repository setup](https://github.com/Provable-Games/evm-starknet-address-registry#setup), run from the root:

```sh
npm run format:check
npm run build
npm run lint
npm run typecheck
npm run test:coverage
npm run check:package
```

Unit tests use mocked adapters. The [local integration suite](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/scripts/integration/README.md)
executes the built SDK with the contract and disposable software keys.
[Mainnet](https://voyager.online/contract/0x00c865a977617dc70027c0a7b455ed5a34d1ad615267d8bf5359747a56b31337) and [Sepolia](https://github.com/Provable-Games/evm-starknet-address-registry/blob/main/deployments/sepolia.json)
deployments are recorded separately.
