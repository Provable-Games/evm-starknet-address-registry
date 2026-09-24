import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

export function checkSdkProtocolIdentity(
  abi: Uint8Array,
  provenance: { abi_sha256: string; approved_signing_revision: string },
  sdk: { ABI_SHA256: string; PROTOCOL_REVISION: string },
): void {
  assert.equal(
    createHash('sha256').update(abi).digest('hex'),
    provenance.abi_sha256,
    'Frozen ABI bytes differ from provenance',
  );
  assert.equal(sdk.ABI_SHA256, provenance.abi_sha256, 'SDK ABI identity drift');
  assert.equal(
    sdk.PROTOCOL_REVISION,
    provenance.approved_signing_revision,
    'SDK signing revision drift',
  );
}
