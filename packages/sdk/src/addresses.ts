import { getAddress } from 'viem/utils';
import { requireInput } from './errors.js';
import type { AccountAddress, EthereumAddress, Hash32 } from './protocol.js';

export const FELT_PRIME = (1n << 251n) + 17n * (1n << 192n) + 1n;
export const ZERO_ACCOUNT: AccountAddress = `0x${'0'.repeat(64)}`;
export function unsigned(value: unknown, bits: number): bigint {
  requireInput(
    typeof value === 'bigint' && value >= 0n && value < 1n << BigInt(bits),
    `Expected uint${String(bits)}`,
  );
  return value;
}
export function ethereumAddress(value: unknown): EthereumAddress {
  requireInput(
    typeof value === 'string' && /^0x[0-9a-fA-F]{40}$/.test(value),
    'Expected full 20-byte Ethereum address',
  );
  const lower = value.toLowerCase() as EthereumAddress;
  requireInput(
    value === lower ||
      value === `0x${value.slice(2).toUpperCase()}` ||
      value === getAddress(lower),
    'Invalid Ethereum address checksum',
  );
  return lower;
}
export function hash32(value: unknown): Hash32 {
  requireInput(
    typeof value === 'string' && /^0x[0-9a-fA-F]{64}$/.test(value),
    'Expected full 32-byte word',
  );
  return value.toLowerCase() as Hash32;
}
export function accountAddress(value: unknown): AccountAddress {
  const result = hash32(value);
  unsigned(BigInt(result), 251); // ContractAddress < 2^251; StorageBaseAddress < 2^251 - 256.
  return result;
}
export function feltHash(value: unknown): Hash32 {
  const result = hash32(value);
  requireInput(BigInt(result) < FELT_PRIME, 'Hash exceeds native felt range');
  return result;
}
export function nonzero<T extends EthereumAddress>(value: T): T {
  requireInput(BigInt(value) !== 0n, 'Zero address is not allowed');
  return value;
}
export function word(value: bigint): Hash32 {
  return `0x${unsigned(value, 256).toString(16).padStart(64, '0')}`;
}
export function rpcInteger(value: unknown): bigint {
  requireInput(
    typeof value === 'string' &&
      /^(?:0x[0-9a-fA-F]+|0|[1-9][0-9]*)$/.test(value),
    'Invalid RPC integer',
  );
  const result = BigInt(value);
  requireInput(result < FELT_PRIME, 'RPC value exceeds native felt range');
  return result;
}
export function limbs(value: bigint): readonly [string, string] {
  unsigned(value, 256);
  return [(value & ((1n << 128n) - 1n)).toString(), (value >> 128n).toString()];
}
export function fromLimbs(low: unknown, high: unknown): bigint {
  return (
    unsigned(rpcInteger(low), 128) + (unsigned(rpcInteger(high), 128) << 128n)
  );
}
