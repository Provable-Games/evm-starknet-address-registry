# EVM–Starknet Address Registry

An immutable Starknet registry and TypeScript SDK for associating Ethereum addresses
with Starknet accounts. Each Ethereum address has at most one active destination in a
registry; a Starknet account can receive links from many Ethereum addresses.

The [Starknet Mainnet registry](deployments/mainnet.json) uses the `Loot Survivor`
label at `0x00c865a977617dc70027c0a7b455ed5a34d1ad615267d8bf5359747a56b31337`.

Ethereum signatures authorize link, move, and revoke requests. The destination
account authorizes incoming links and moves; the linked account can unlink, and an
account can cancel its pending incoming consent. Nonces prevent replay. The registry
provides lookup and pagination, while asset and application policy remain with
consumers.

## Repository guide

- [Contract](contracts/README.md): entrypoints, class identity, and local checks.
- [SDK](packages/sdk/README.md): authenticated reads, signing, and submission adapters.
- [Protocol artifacts](protocol/README.md): frozen ABI, independent vectors, and validation.
- [Local integration](scripts/integration/README.md): SDK and contract execution on Devnet.
- [Client](examples/client/README.md) and [consumer contract](examples/consumer/README.md): integration examples.

## Setup

On Linux x64 or ARM64 with glibc, install Git and Python 3.12 or newer. From the
repository root:

```sh
python3 scripts/setup.py
export PATH="$PWD/.tools/bin:$PATH"
unset UNIVERSAL_SIERRA_COMPILER
python3 scripts/check_bootstrap.py
npm ci
```

`toolchain.json` pins tool versions and download hashes. Setup installs tools under
`.tools`.

## Checks

```sh
scarb --manifest-path contracts/Scarb.toml fmt --check
scarb --manifest-path contracts/Scarb.toml lint --test --deny-warnings
scarb --manifest-path contracts/Scarb.toml build
python3 scripts/run_cairo_tests.py
npm run format:check
npm run build
npm run lint
npm run typecheck
npm run test:coverage
npm run check:package
```
