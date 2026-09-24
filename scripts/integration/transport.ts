import assert from 'node:assert/strict';
import { createNativeAccount, nativeSelector } from './starknet-runtime.mjs';
import {
  accountAddress,
  feltHash,
  word,
  type AccountAdapter,
  type Hash32,
  type RegistryTransport,
  type TransactionReceipt,
} from '@provable-games/evm-starknet-address-registry';

export const CHAIN_ID = BigInt('0x534e5f5345504f4c4941');

export function localRpc(url: string) {
  const parsed = new URL(url);
  assert.equal(parsed.protocol, 'http:');
  assert.equal(parsed.hostname, '127.0.0.1');
  assert.equal(
    parsed.username + parsed.password + parsed.search + parsed.hash,
    '',
  );
  return async (method: string, params: object = {}): Promise<unknown> => {
    const response = await fetch(url, {
      method: 'POST',
      redirect: 'error',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
      signal: AbortSignal.timeout(30_000),
    });
    assert(response.ok, `RPC HTTP ${String(response.status)}`);
    const value: unknown = await response.json();
    assert(value && typeof value === 'object');
    if ('error' in value) throw new Error(JSON.stringify(value.error));
    assert('result' in value);
    return value.result;
  };
}
export type LocalRpc = ReturnType<typeof localRpc>;
export function object(value: unknown): Record<string, unknown> {
  assert(value && typeof value === 'object' && !Array.isArray(value));
  return value as Record<string, unknown>;
}
export function hex(value: unknown): Hash32 {
  assert.equal(typeof value, 'string');
  assert(/^0x[0-9a-f]+$/i.test(value as string));
  return feltHash(word(BigInt(value as string)));
}

export function transport(rpc: LocalRpc): RegistryTransport {
  return {
    async getBlock(blockHash) {
      const value = object(
        await rpc('starknet_getBlockWithTxHashes', {
          block_id: blockHash ? { block_hash: blockHash } : 'latest',
        }),
      );
      assert.equal(typeof value.timestamp, 'number');
      assert(Number.isSafeInteger(value.timestamp));
      return {
        blockHash: hex(value.block_hash),
        timestamp: BigInt(value.timestamp as number),
      };
    },
    async getChainId() {
      return BigInt(hex(await rpc('starknet_chainId')));
    },
    async getClassHash(registryAddress, blockHash) {
      return hex(
        await rpc('starknet_getClassHashAt', {
          contract_address: registryAddress,
          block_id: { block_hash: blockHash },
        }),
      );
    },
    async call(call, blockHash) {
      const value = await rpc('starknet_call', {
        request: {
          contract_address: call.contractAddress,
          entry_point_selector: nativeSelector(call.entrypoint),
          calldata: call.calldata.map(
            (felt) => `0x${BigInt(felt).toString(16)}`,
          ),
        },
        block_id: { block_hash: blockHash },
      });
      assert(
        Array.isArray(value) &&
          value.every((felt: unknown) => typeof felt === 'string'),
      );
      return value;
    },
  };
}

export async function receipt(
  rpc: LocalRpc,
  transactionHash: Hash32,
): Promise<TransactionReceipt> {
  const raw = object(
    await rpc('starknet_getTransactionReceipt', {
      transaction_hash: transactionHash,
    }),
  );
  assert.equal(hex(raw.transaction_hash), transactionHash);
  assert(['SUCCEEDED', 'REVERTED'].includes(String(raw.execution_status)));
  return {
    transactionHash,
    blockHash: hex(raw.block_hash),
    status: raw.execution_status === 'SUCCEEDED' ? 'succeeded' : 'reverted',
  };
}

/** Dev-only: captures a private, immutable account and endpoint; no wallet connector can mutate it. */
export function fixedAccount(
  url: string,
  address: string,
  publicTestPrivateKey: string,
) {
  const rpc = localRpc(url);
  const canonical = accountAddress(hex(address));
  const account = createNativeAccount(url, canonical, publicTestPrivateKey);
  const adapter: AccountAdapter = {
    generation: () => 0n,
    subscribeChange: () => () => {
      /* Identity and chain configuration are immutable. */
    },
    async identity() {
      assert.equal(BigInt(hex(await rpc('starknet_chainId'))), CHAIN_ID);
      return { address: canonical, chainId: CHAIN_ID };
    },
    async simulate(calls) {
      await account.simulate(calls);
    },
    async execute(calls) {
      const result = object(await account.execute(calls));
      return hex(result.transaction_hash);
    },
    async wait(transactionHash) {
      await account.wait(transactionHash);
      return receipt(rpc, transactionHash);
    },
  };
  return { adapter, account };
}
