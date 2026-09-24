import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  ABI_SHA256,
  PROTOCOL_REVISION,
  accountAddress,
  createRegistryReader,
  type TrustedDeployment,
} from '@provable-games/evm-starknet-address-registry';
import {
  hex,
  localRpc,
  object,
  receipt,
  transport,
} from '../integration/transport.ts';
import { artifactIdentity } from './identity.ts';

const inputPath = process.argv[2];
assert(inputPath, 'Pass a private local readback request');
const input = object(JSON.parse(readFileSync(inputPath, 'utf8')) as unknown);
const config = object(input.config);
const identity = object(input.identity);
const local = object(input.local);
assert.equal(typeof local.url, 'string');
const rpc = localRpc(local.url as string);
assert.deepEqual(
  identity,
  artifactIdentity(),
  'Build identity changed after planning',
);
assert.equal(await rpc('starknet_specVersion'), '0.10.2');
const registry = object(
  object(local.deployed).EthereumAddressAssociationRegistry,
);
assert.equal(
  hex(registry.class_hash),
  hex(identity.class_hash),
  'Declared class differs from compiled artifact',
);
assert.equal(typeof config.account_label, 'string');
assert.equal(config.ethereum_chain_id, '11155111');
assert.equal(config.account_chain_id, '0x534e5f5345504f4c4941');
const deployment: TrustedDeployment = {
  ethereumChainId: 11155111n,
  accountChainId: BigInt(config.account_chain_id),
  registryAddress: accountAddress(hex(registry.contract_address)),
  classHash: hex(identity.class_hash),
  accountLabel: config.account_label as string,
  abiSha256: ABI_SHA256,
  protocolRevision: PROTOCOL_REVISION,
};
const receipts = await Promise.all([
  receipt(rpc, hex(registry.declare_transaction_hash)),
  receipt(rpc, hex(registry.transaction_hash)),
]);
assert(
  receipts.every((value) => value.status === 'succeeded'),
  'Declaration or deployment failed',
);
const deployedReceipt = receipts[1];
assert(deployedReceipt);
const adapter = transport(rpc);
const block = await adapter.getBlock(deployedReceipt.blockHash);
assert.equal(block.blockHash, deployedReceipt.blockHash);
const reader = createRegistryReader(deployment, adapter);
const domain = await reader.getSigningDomain(block.blockHash);
const version = await reader.getVersion(block.blockHash);
assert.equal(version, 49n);
console.log(
  JSON.stringify(
    { deployment, domain, native_version: version, block, receipts },
    (_, value: unknown) =>
      typeof value === 'bigint' ? value.toString() : value,
  ),
);
