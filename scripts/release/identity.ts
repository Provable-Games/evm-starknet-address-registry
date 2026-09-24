import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { classHash } from './class-hash.mjs';
import { object } from '../integration/transport.ts';
import { checkSdkProtocolIdentity } from '../sdk-protocol-identity.ts';
import * as sdk from '@provable-games/evm-starknet-address-registry';

export function artifactIdentity() {
  const compiled = object(
    JSON.parse(
      readFileSync(
        'contracts/target/dev/contracts_EthereumAddressAssociationRegistry.contract_class.json',
        'utf8',
      ),
    ) as unknown,
  );
  const abi = readFileSync('protocol/abi.json');
  const provenance = object(
    JSON.parse(readFileSync('protocol/abi.provenance.json', 'utf8')) as unknown,
  );
  assert.equal(typeof provenance.abi_sha256, 'string');
  assert.equal(typeof provenance.approved_signing_revision, 'string');
  checkSdkProtocolIdentity(
    abi,
    {
      abi_sha256: provenance.abi_sha256 as string,
      approved_signing_revision: provenance.approved_signing_revision as string,
    },
    sdk,
  );
  assert.deepEqual(compiled.abi, JSON.parse(abi.toString()) as unknown);
  return {
    class_hash: classHash(compiled),
    abi_sha256: sdk.ABI_SHA256,
    protocol_revision: sdk.PROTOCOL_REVISION,
  };
}
if (
  process.argv[1]?.endsWith('/identity.ts') ||
  process.argv[1] === 'scripts/release/identity.ts'
) {
  console.log(JSON.stringify(artifactIdentity()));
}
