/** Independent frozen synthetic oracle fixtures. All adapters in these tests are mocks. */
import { readFileSync } from 'node:fs';
import { vi } from 'vitest';
import type {
  AccountAdapter,
  BlockSnapshot,
  RegistryReader,
  SignedRequest,
  TrustedDeployment,
  TypedData,
} from '../src/protocol.js';
import {
  accountAddress,
  ethereumAddress,
  word,
  ZERO_ACCOUNT,
} from '../src/addresses.js';
import {
  ABI_SHA256,
  prepareRequest,
  PROTOCOL_REVISION,
  signingDomain,
} from '../src/typed-data.js';
import { parseSignature } from '../src/signature.js';
export interface Fixture {
  id: string;
  account_label: string;
  typed_data: TypedData;
  hashes: {
    salt: `0x${string}`;
    domain_separator: `0x${string}`;
    digest: `0x${string}`;
    struct_hash: `0x${string}`;
  };
  signature: {
    v_0_1: string;
    v_27_28: string;
    erc2098: string;
    r: string;
    s: string;
    y_parity: number;
  };
  calldata: { full: string[]; entrypoint: string };
}
interface UnsignedFixture {
  id: string;
  entrypoint: 'unlink' | 'invalidate_pending_incoming';
  calldata: [string];
}
const vectorArtifact = JSON.parse(
  readFileSync(
    new URL('../../../protocol/vectors.json', import.meta.url),
    'utf8',
  ),
) as {
  vectors: Fixture[];
  unsigned_vectors: UnsignedFixture[];
  deployments: unknown[];
};
export const fixtures = vectorArtifact.vectors;
export const unsignedFixtures = vectorArtifact.unsigned_vectors;
export function fixtureState(fixture: Fixture) {
  const data = fixture.typed_data;
  const deployment: TrustedDeployment = {
    ethereumChainId: BigInt(data.domain.chainId) as 1n | 11155111n,
    accountChainId: BigInt(data.message.accountChainId),
    registryAddress: data.message.registryAddress,
    classHash: word(123n),
    accountLabel: fixture.account_label,
    protocolRevision: PROTOCOL_REVISION,
    abiSha256: ABI_SHA256,
  };
  const operation =
    data.primaryType === 'LinkAddress'
      ? 'link'
      : data.primaryType === 'MoveAddress'
        ? 'move'
        : 'revoke';
  const snapshot: BlockSnapshot = {
    blockHash: word(44n),
    timestamp: 1000n,
    classHash: deployment.classHash,
    signingDomain: signingDomain(deployment),
    ethereumAddress: ethereumAddress(data.message.ethereumAddress),
    accountAddress:
      data.primaryType === 'RevokeAssociation'
        ? deployment.registryAddress
        : data.message.accountAddress,
    currentAccountAddress:
      data.primaryType === 'LinkAddress'
        ? ZERO_ACCOUNT
        : data.primaryType === 'MoveAddress'
          ? data.message.previousAccountAddress
          : data.message.currentAccountAddress,
    ethereumNonce: BigInt(data.message.ethereumNonce),
    recipientNonce:
      data.primaryType === 'RevokeAssociation'
        ? 9n
        : BigInt(data.message.recipientNonce),
  };
  const prepared = prepareRequest(
    deployment,
    snapshot,
    operation,
    BigInt(data.message.deadline),
  );
  const signed: SignedRequest = {
    prepared,
    signature: parseSignature(fixture.signature.v_0_1),
    recoveredAddress: snapshot.ethereumAddress,
  };
  return { deployment, snapshot, prepared, signed };
}
export function firstFixture(): Fixture {
  const result = fixtures[0];
  if (!result) throw new Error('Missing frozen fixture');
  return result;
}
export function mocks(fixture = firstFixture()) {
  const state = fixtureState(fixture);
  const reader = {
    deployment: state.deployment,
    snapshot: vi.fn<RegistryReader['snapshot']>(
      async (_d, ethereum, account) => {
        await Promise.resolve();
        return {
          ...state.snapshot,
          ethereumAddress: ethereumAddress(ethereum),
          accountAddress: accountAddress(account),
        };
      },
    ),
    getSigningDomain: vi.fn<RegistryReader['getSigningDomain']>(async () => {
      await Promise.resolve();
      return state.snapshot.signingDomain;
    }),
    getVersion: vi.fn<RegistryReader['getVersion']>(async () => {
      await Promise.resolve();
      return 49n;
    }),
    getStarknetAddress: vi.fn<RegistryReader['getStarknetAddress']>(
      async () => {
        await Promise.resolve();
        return state.snapshot.currentAccountAddress;
      },
    ),
    getEthereumNonce: vi.fn<RegistryReader['getEthereumNonce']>(async () => {
      await Promise.resolve();
      return state.snapshot.ethereumNonce;
    }),
    getRecipientNonce: vi.fn<RegistryReader['getRecipientNonce']>(async () => {
      await Promise.resolve();
      return state.snapshot.recipientNonce;
    }),
    isAssociated: vi.fn<RegistryReader['isAssociated']>(async () => {
      await Promise.resolve();
      return false;
    }),
    getEthereumAddressCount: vi.fn<RegistryReader['getEthereumAddressCount']>(
      async () => {
        await Promise.resolve();
        return 0n;
      },
    ),
    getEthereumAddresses: vi.fn<RegistryReader['getEthereumAddresses']>(
      async () => {
        await Promise.resolve();
        return [];
      },
    ),
    listAllEthereumAddresses: vi.fn<RegistryReader['listAllEthereumAddresses']>(
      async (account, block) => {
        await Promise.resolve();
        return {
          deployment: state.deployment,
          accountAddress: account,
          blockHash: block,
          ethereumAddresses: [],
        };
      },
    ),
  } satisfies RegistryReader;
  const account = {
    generation: vi.fn<AccountAdapter['generation']>(() => 0n),
    subscribeChange: vi.fn<AccountAdapter['subscribeChange']>(() => vi.fn()),
    identity: vi.fn<AccountAdapter['identity']>(async () => {
      await Promise.resolve();
      return {
        address: state.snapshot.accountAddress,
        chainId: state.deployment.accountChainId,
      };
    }),
    simulate: vi.fn<AccountAdapter['simulate']>(async () => {
      await Promise.resolve();
      return undefined;
    }),
    execute: vi.fn<AccountAdapter['execute']>(async () => {
      await Promise.resolve();
      return word(66n);
    }),
    wait: vi.fn<AccountAdapter['wait']>(async (transactionHash) => {
      await Promise.resolve();
      return {
        transactionHash,
        blockHash: word(77n),
        status: 'succeeded' as const,
      };
    }),
  } satisfies AccountAdapter;
  return { ...state, reader, account };
}
