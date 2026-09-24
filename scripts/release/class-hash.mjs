// Dev-only pinned starknet.js bridge, matching integration/starknet-runtime.mjs.
// Keeps the upstream WalletAccountV6 declaration incompatibility out of TypeScript.
import { hash } from 'starknet';
export function classHash(compiled) {
  return hash.computeContractClassHash(compiled);
}
