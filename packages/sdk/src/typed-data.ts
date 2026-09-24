import {
  concatHex,
  hashStruct,
  hashTypedData,
  keccak256,
  stringToHex,
  getAddress,
} from 'viem/utils';
import {
  accountAddress,
  ethereumAddress,
  feltHash,
  hash32,
  nonzero,
  unsigned,
  word,
  ZERO_ACCOUNT,
} from './addresses.js';
import { exactKeys, failure, isValue, requireInput } from './errors.js';
import type {
  BlockSnapshot,
  Hash32,
  Operation,
  PreparedRequest,
  SigningDomain,
  TrustedDeployment,
  TypedData,
} from './protocol.js';

export const PROTOCOL_REVISION = '5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a';
export const ABI_SHA256 =
  '7a5bfdd9bab5b56c78a403d964534ec2a5b8711705152b59094d5939820224eb';
const domainFields = [
  { name: 'name', type: 'string' },
  { name: 'version', type: 'string' },
  { name: 'chainId', type: 'uint256' },
  { name: 'salt', type: 'bytes32' },
] as const;
const linkFields = [
  { name: 'statement', type: 'string' },
  { name: 'ethereumAddress', type: 'address' },
  { name: 'accountAddress', type: 'bytes32' },
  { name: 'accountChainId', type: 'uint256' },
  { name: 'registryAddress', type: 'bytes32' },
  { name: 'ethereumNonce', type: 'uint256' },
  { name: 'recipientNonce', type: 'uint256' },
  { name: 'deadline', type: 'uint64' },
] as const;
// An explicit tuple keeps the frozen MoveAddress field order visible to declarations and review.
const moveTypes = [
  linkFields[0],
  linkFields[1],
  linkFields[2],
  { name: 'previousAccountAddress', type: 'bytes32' },
  linkFields[3],
  linkFields[4],
  linkFields[5],
  linkFields[6],
  linkFields[7],
] as const;
const revokeFields = [
  linkFields[0],
  linkFields[1],
  { name: 'currentAccountAddress', type: 'bytes32' },
  linkFields[3],
  linkFields[4],
  linkFields[5],
  linkFields[7],
] as const;
export function deployment(value: TrustedDeployment): TrustedDeployment {
  exactKeys(value, [
    'ethereumChainId',
    'accountChainId',
    'registryAddress',
    'classHash',
    'accountLabel',
    'protocolRevision',
    'abiSha256',
  ]);
  requireInput(
    (value.ethereumChainId === 1n &&
      value.accountChainId === 0x534e5f4d41494en) ||
      (value.ethereumChainId === 11155111n &&
        value.accountChainId === 0x534e5f5345504f4c4941n),
    'Unsupported chain pair',
  );
  requireInput(
    typeof value.accountLabel === 'string' &&
      value.accountLabel.length <= 48 &&
      /^[A-Za-z0-9]+(?: [A-Za-z0-9]+)*$/.test(value.accountLabel),
    'Invalid immutable account label',
  );
  requireInput(
    isValue(value.protocolRevision, PROTOCOL_REVISION) &&
      value.abiSha256 === ABI_SHA256,
    'Unsupported protocol or ABI identity',
  );
  return {
    ...value,
    registryAddress: nonzero(accountAddress(value.registryAddress)),
    classHash: nonzero(feltHash(value.classHash)),
  };
}
export function signingDomain(input: TrustedDeployment): SigningDomain {
  const d = deployment(input);
  const salt = keccak256(
    concatHex([
      keccak256(stringToHex('Account Address Association/v1')),
      word(d.accountChainId),
      d.registryAddress,
    ]),
  );
  const domain = {
    name: 'Account Address Association' as const,
    version: '1' as const,
    chainId: d.ethereumChainId,
    salt,
  };
  return {
    name: domain.name,
    version: domain.version,
    ethereumChainId: d.ethereumChainId,
    accountChainId: d.accountChainId,
    registryAddress: d.registryAddress,
    salt,
    domainSeparator: hashStruct({
      data: domain,
      primaryType: 'EIP712Domain',
      types: { EIP712Domain: domainFields },
    }),
    accountLabel: d.accountLabel,
    linkStatement: `Link my Ethereum address to this ${d.accountLabel} account. This does not approve asset transfers.`,
    moveStatement: `Move my Ethereum address link from the previous ${d.accountLabel} account shown here to this account. This does not approve asset transfers.`,
    revokeStatement: `Remove my Ethereum address link to the ${d.accountLabel} account shown here, if any, and cancel requests using the current Ethereum nonce.`,
    accountNetworkName:
      d.ethereumChainId === 1n ? 'Starknet Mainnet' : 'Starknet Sepolia',
  };
}
export function authenticateDomain(
  d: TrustedDeployment,
  actual: SigningDomain,
): void {
  const expected = signingDomain(d);
  exactKeys(actual, Object.keys(expected));
  requireInput(
    Object.entries(expected).every(
      ([key, value]) => actual[key as keyof SigningDomain] === value,
    ),
    'Registry signing domain differs from trusted deployment',
  );
}
export function checkedSnapshot(
  d: TrustedDeployment,
  value: BlockSnapshot,
): BlockSnapshot {
  exactKeys(value, [
    'blockHash',
    'timestamp',
    'classHash',
    'signingDomain',
    'ethereumAddress',
    'accountAddress',
    'currentAccountAddress',
    'ethereumNonce',
    'recipientNonce',
  ]);
  authenticateDomain(d, value.signingDomain);
  requireInput(
    feltHash(value.classHash) === d.classHash,
    'Registry class identity changed',
  );
  return {
    signingDomain: signingDomain(d),
    blockHash: feltHash(value.blockHash),
    timestamp: unsigned(value.timestamp, 64),
    classHash: feltHash(value.classHash),
    ethereumAddress: ethereumAddress(value.ethereumAddress),
    accountAddress: nonzero(accountAddress(value.accountAddress)),
    currentAccountAddress: accountAddress(value.currentAccountAddress),
    ethereumNonce: unsigned(value.ethereumNonce, 256),
    recipientNonce: unsigned(value.recipientNonce, 256),
  };
}
export function prepareRequest(
  dInput: TrustedDeployment,
  snapshotInput: BlockSnapshot,
  operation: Operation,
  deadlineInput?: bigint,
): PreparedRequest {
  const d = deployment(dInput),
    snapshot = checkedSnapshot(d, snapshotInput),
    discovery = signingDomain(d);
  const deadline = unsigned(deadlineInput ?? snapshot.timestamp + 900n, 64);
  requireInput(deadline !== 0n, 'Deadline must be nonzero');
  if (deadline < snapshot.timestamp)
    throw failure('expired', 'prepare', 'Request deadline has passed');
  const ethereum = nonzero(snapshot.ethereumAddress);
  const domain = {
    name: discovery.name,
    version: discovery.version,
    chainId: d.ethereumChainId.toString(),
    salt: discovery.salt,
  };
  const base = { deployment: d, snapshot };
  const common = {
    ethereumAddress: ethereum,
    accountAddress: snapshot.accountAddress,
    ethereumNonce: snapshot.ethereumNonce,
    recipientNonce: snapshot.recipientNonce,
    deadline,
  };
  const message = {
    ethereumAddress: ethereum,
    accountAddress: snapshot.accountAddress,
    accountChainId: d.accountChainId.toString(),
    registryAddress: d.registryAddress,
    ethereumNonce: snapshot.ethereumNonce.toString(),
    recipientNonce: snapshot.recipientNonce.toString(),
    deadline: deadline.toString(),
  };
  if (operation === 'link') {
    requireInput(
      snapshot.currentAccountAddress === ZERO_ACCOUNT,
      'Link requires an unlinked Ethereum address',
    );
    const typedData: Extract<TypedData, { primaryType: 'LinkAddress' }> = {
      types: { EIP712Domain: domainFields, LinkAddress: linkFields },
      primaryType: 'LinkAddress',
      domain,
      message: { statement: discovery.linkStatement, ...message },
    };
    return immutable({
      ...base,
      operation,
      request: common,
      typedData,
      digest: typedDigest(typedData),
    });
  }
  if (operation === 'move') {
    requireInput(
      snapshot.currentAccountAddress !== ZERO_ACCOUNT &&
        snapshot.currentAccountAddress !== snapshot.accountAddress,
      'Move requires a distinct linked previous account',
    );
    const typedData: Extract<TypedData, { primaryType: 'MoveAddress' }> = {
      types: { EIP712Domain: domainFields, MoveAddress: moveTypes },
      primaryType: 'MoveAddress',
      domain,
      message: {
        statement: discovery.moveStatement,
        ethereumAddress: ethereum,
        accountAddress: snapshot.accountAddress,
        previousAccountAddress: snapshot.currentAccountAddress,
        accountChainId: message.accountChainId,
        registryAddress: message.registryAddress,
        ethereumNonce: message.ethereumNonce,
        recipientNonce: message.recipientNonce,
        deadline: message.deadline,
      },
    };
    return immutable({
      ...base,
      operation,
      request: {
        ethereumAddress: ethereum,
        accountAddress: common.accountAddress,
        previousAccountAddress: snapshot.currentAccountAddress,
        ethereumNonce: common.ethereumNonce,
        recipientNonce: common.recipientNonce,
        deadline,
      },
      typedData,
      digest: typedDigest(typedData),
    });
  }
  requireInput(isValue(operation, 'revoke'), 'Unknown operation');
  const typedData: Extract<TypedData, { primaryType: 'RevokeAssociation' }> = {
    types: { EIP712Domain: domainFields, RevokeAssociation: revokeFields },
    primaryType: 'RevokeAssociation',
    domain,
    message: {
      statement: discovery.revokeStatement,
      ethereumAddress: ethereum,
      currentAccountAddress: snapshot.currentAccountAddress,
      accountChainId: message.accountChainId,
      registryAddress: message.registryAddress,
      ethereumNonce: message.ethereumNonce,
      deadline: message.deadline,
    },
  };
  return immutable({
    ...base,
    operation,
    request: {
      ethereumAddress: ethereum,
      currentAccountAddress: snapshot.currentAccountAddress,
      ethereumNonce: common.ethereumNonce,
      deadline,
    },
    typedData,
    digest: typedDigest(typedData),
  });
}
export function typedDigest(typedData: TypedData): Hash32 {
  return hashTypedData<Record<string, unknown>, string>({
    ...typedData,
    domain: { ...typedData.domain, chainId: BigInt(typedData.domain.chainId) },
  });
}
/** Detached wallet/display representation; internal requests always retain lowercase addresses. */
export function walletTypedData(typedData: TypedData): TypedData {
  const copy = JSON.parse(JSON.stringify(typedData)) as TypedData;
  return {
    ...copy,
    message: {
      ...copy.message,
      ethereumAddress: getAddress(
        ethereumAddress(copy.message.ethereumAddress),
      ),
    },
  } as TypedData;
}
function equalData(left: unknown, right: unknown): boolean {
  if (
    typeof left !== 'object' ||
    left === null ||
    typeof right !== 'object' ||
    right === null
  )
    return left === right;
  const a = Object.entries(left),
    b = Object.entries(right);
  return (
    a.length === b.length &&
    a.every(
      ([key, value]) =>
        Object.hasOwn(right, key) &&
        equalData(value, (right as Record<string, unknown>)[key]),
    )
  );
}
export function authenticatePrepared(input: PreparedRequest): PreparedRequest {
  const expected = prepareRequest(
    input.deployment,
    input.snapshot,
    input.operation,
    input.request.deadline,
  );
  requireInput(
    equalData(input, expected),
    'Prepared request is not the exact authenticated operation',
  );
  hash32(input.digest);
  return expected;
}

function immutable<T>(value: T): T {
  if (typeof value === 'object' && value !== null) {
    for (const member of Object.values(value)) immutable(member);
    Object.freeze(value);
  }
  return value;
}
