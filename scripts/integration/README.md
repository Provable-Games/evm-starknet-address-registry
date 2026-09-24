# Local registry integration

The integration suite runs the built SDK and production registry on a fresh,
private Starknet Devnet configured as `SN_SEPOLIA`. It declares and deploys the
registry and consumer examples through account-signed transactions, then checks
class/ABI identity and SDK-authenticated reads.

The run exercises signed link, move, and revoke; account-authorized unlink and
pending-consent cancellation; pagination; nonce and signature rejection; and
consumer policy during execution. It uses disposable software keys.

## Run locally

From the repository root:

```sh
python3 scripts/setup.py --components node npm scarb foundry starknet-devnet
export PATH="$PWD/.tools/bin:/usr/bin:/bin"
unset UNIVERSAL_SIERRA_COMPILER
npm ci
npm run build
python3 scripts/integration/run.py
```

The runner records commands, tool versions, artifact hashes, transactions, and
readback under a fresh `.tools/integration-evidence/run-*` directory. It stops its
owned Devnet and removes disposable account material on normal exit and handled
termination. The [Sepolia deployment record](../../deployments/sepolia.json) is
separate from this local suite.

The local Starknet transport uses `starknet-runtime.mjs` because the installed
starknet.js 10.8.0 declarations conflict with the repository's strict TypeScript
6.0.3 settings. The JavaScript bridge validates external results at its typed
boundary; it does not change the packed SDK runtime.

## Local release rehearsal

[`scripts/release/local.py`](../release/local.py) prepares a local-only deployment
plan or executes a fresh registry deployment with authenticated SDK readback.
Use [`local.example.json`](../release/local.example.json) and a new output path:

```sh
mkdir -p .tools/release-records
python3 scripts/release/local.py plan --config scripts/release/local.example.json --output .tools/release-records/plan.json
python3 scripts/release/local.py deploy-local --config scripts/release/local.example.json --output .tools/release-records/deployment.json
```

The helper accepts only loopback Devnet configuration and refuses existing output
files. A `local-deployment-success` record contains the deployment and readback;
a plan alone does not establish execution.
