import { describe, expect, test } from 'vitest';
import { hashStruct } from 'viem/utils';
import {
  accountAddress,
  ethereumAddress,
  feltHash,
  FELT_PRIME,
  fromLimbs,
  hash32,
  limbs,
  nonzero,
  rpcInteger,
  unsigned,
  word,
  ZERO_ACCOUNT,
} from '../src/addresses.js';
import {
  authenticatePrepared,
  deployment,
  prepareRequest,
  signingDomain,
  typedDigest,
  walletTypedData,
} from '../src/typed-data.js';
import {
  checkedSignature,
  encodeSigned,
  parseSignature,
  recoverSigner,
  SECP256K1_ORDER,
  signatureHex,
} from '../src/signature.js';
import {
  failure,
  providerFailure,
  confirmationUnavailable,
} from '../src/errors.js';
import type {
  BlockSnapshot,
  Operation,
  PreparedRequest,
  Signature,
  TrustedDeployment,
} from '../src/protocol.js';
import { fixtures, fixtureState, firstFixture } from './fixtures.js';

describe('independent frozen oracle parity (synthetic keys only)', () => {
  for (const fixture of fixtures)
    test(fixture.id, async () => {
      const { deployment, prepared, signed } = fixtureState(fixture);
      expect(walletTypedData(prepared.typedData)).toEqual(fixture.typed_data);
      expect(JSON.stringify(walletTypedData(prepared.typedData))).toBe(
        JSON.stringify(fixture.typed_data),
      );
      expect(prepared.typedData.message.ethereumAddress).toBe(
        fixture.typed_data.message.ethereumAddress.toLowerCase(),
      );
      expect(signingDomain(deployment).salt).toBe(fixture.hashes.salt);
      expect(signingDomain(deployment).domainSeparator).toBe(
        fixture.hashes.domain_separator,
      );
      expect(prepared.digest).toBe(fixture.hashes.digest);
      expect(typedDigest(fixture.typed_data)).toBe(prepared.digest);
      expect(
        hashStruct({
          data: prepared.typedData.message,
          primaryType: prepared.typedData.primaryType,
          types: prepared.typedData.types,
        }),
      ).toBe(fixture.hashes.struct_hash);
      for (const encoding of [
        fixture.signature.v_0_1,
        fixture.signature.v_27_28,
        fixture.signature.erc2098,
      ]) {
        const signature = parseSignature(encoding);
        expect(signature).toEqual({
          r: BigInt(fixture.signature.r),
          s: BigInt(fixture.signature.s),
          yParity: fixture.signature.y_parity === 1,
        });
        expect(
          await recoverSigner(
            prepared.digest,
            signature,
            prepared.request.ethereumAddress,
          ),
        ).toBe(signed.recoveredAddress);
        expect(signatureHex(signature)).toBe(fixture.signature.v_27_28);
      }
      expect(encodeSigned(signed).calldata).toEqual(fixture.calldata.full);
      expect(encodeSigned(signed).entrypoint).toBe(fixture.calldata.entrypoint);
      expect(authenticatePrepared(prepared)).toEqual(prepared);
      expect(Object.isFrozen(prepared.typedData.types)).toBe(true);
      expect(walletTypedData(prepared.typedData)).not.toBe(prepared.typedData);
    });
});
test('lossless address/integer boundaries and checksum validation', () => {
  const e = firstFixture().typed_data.message.ethereumAddress;
  expect(ethereumAddress(e)).toBe(e.toLowerCase());
  expect(ethereumAddress(`0x${e.slice(2).toUpperCase()}`)).toBe(
    e.toLowerCase(),
  );
  for (const bad of [
    0,
    null,
    '0x1',
    '0x' + 'f'.repeat(42),
    e.replace('E', 'e'),
  ])
    expect(() => ethereumAddress(bad)).toThrow();
  expect(accountAddress(word((1n << 251n) - 1n))).toBe(word((1n << 251n) - 1n));
  expect(feltHash(word(FELT_PRIME - 1n))).toBe(word(FELT_PRIME - 1n));
  expect(hash32(word((1n << 256n) - 1n))).toBe(word((1n << 256n) - 1n));
  expect(() => accountAddress(word(1n << 251n))).toThrow();
  expect(() => feltHash(word(FELT_PRIME))).toThrow();
  for (const bad of [null, '0x1', '0x' + 'z'.repeat(64)])
    expect(() => hash32(bad)).toThrow();
  for (const bad of [-1n, 1n << 64n, 1])
    expect(() => unsigned(bad, 64)).toThrow();
  expect(() => nonzero(ZERO_ACCOUNT)).toThrow();
  expect(rpcInteger('0xABC')).toBe(2748n);
  expect(rpcInteger('0')).toBe(0n);
  for (const bad of ['01', '-1', '0x', '1.2', 1, FELT_PRIME.toString()])
    expect(() => rpcInteger(bad)).toThrow();
  const value = (1n << 255n) + 123n;
  expect(fromLimbs(...limbs(value))).toBe(value);
  expect(() => fromLimbs((1n << 128n).toString(), '0')).toThrow();
});
test('deployment, exact requests, inclusive deadline and operation constraints', () => {
  const { deployment: d, snapshot, prepared } = fixtureState(firstFixture());
  for (const patch of [
    { accountLabel: '' },
    { accountLabel: ' bad' },
    { accountLabel: 'é' },
    { accountLabel: 'x'.repeat(49) },
    { accountChainId: 1n },
    { ethereumChainId: 2n },
    { classHash: ZERO_ACCOUNT },
    { registryAddress: ZERO_ACCOUNT },
    { protocolRevision: 'old' },
    { abiSha256: 'old' },
    { extra: 1 },
  ])
    expect(() => deployment({ ...d, ...patch } as TrustedDeployment)).toThrow();
  expect(prepareRequest(d, snapshot, 'link').request.deadline).toBe(
    snapshot.timestamp + 900n,
  );
  expect(
    prepareRequest(d, snapshot, 'link', snapshot.timestamp).request.deadline,
  ).toBe(snapshot.timestamp);
  for (const deadline of [0n, snapshot.timestamp - 1n, 1n << 64n])
    expect(() => prepareRequest(d, snapshot, 'link', deadline)).toThrow();
  expect(() =>
    prepareRequest(d, { ...snapshot, timestamp: (1n << 64n) - 1n }, 'link'),
  ).toThrow();
  expect(() =>
    prepareRequest(d, { ...snapshot, currentAccountAddress: word(1n) }, 'link'),
  ).toThrow();
  expect(() => prepareRequest(d, snapshot, 'move')).toThrow();
  expect(() =>
    prepareRequest(
      d,
      { ...snapshot, currentAccountAddress: snapshot.accountAddress },
      'move',
    ),
  ).toThrow();
  expect(() => prepareRequest(d, snapshot, 'wrong' as Operation)).toThrow();
  for (const patch of [
    { ethereumAddress: '0x' + '0'.repeat(40) },
    { classHash: word(2n) },
    { ethereumNonce: -1n },
    { recipientNonce: 1n << 256n },
    { signingDomain: { ...snapshot.signingDomain, linkStatement: 'lie' } },
    { signingDomain: { ...snapshot.signingDomain, extra: 1 } },
  ])
    expect(() =>
      prepareRequest(d, { ...snapshot, ...patch } as BlockSnapshot, 'link'),
    ).toThrow();
  for (const patch of [
    { digest: word(1n) },
    { extra: true },
    {
      typedData: {
        ...prepared.typedData,
        message: { ...prepared.typedData.message, extra: true },
      },
    },
    { request: { ...prepared.request, ethereumNonce: 1n } },
  ])
    expect(() =>
      authenticatePrepared({ ...prepared, ...patch } as PreparedRequest),
    ).toThrow();
  expect(typedDigest(prepared.typedData)).toBe(prepared.digest);
});
test('signature invalid lengths, scalars, parity and recovery are rejected', async () => {
  const { signed, prepared } = fixtureState(firstFixture());
  for (const bad of [
    null,
    '',
    '0xzz',
    '0x' + '0'.repeat(128),
    '0x' + '0'.repeat(132),
    firstFixture().signature.v_0_1.slice(0, -2) + '02',
    firstFixture().signature.v_0_1.slice(0, -2) + '25',
  ])
    expect(() => parseSignature(bad)).toThrow();
  for (const patch of [
    { r: 0n },
    { r: SECP256K1_ORDER },
    { s: 0n },
    { s: SECP256K1_ORDER / 2n + 1n },
    { yParity: 1 },
    { r: '1' },
    { s: '1' },
    { extra: 1 },
  ])
    expect(() =>
      checkedSignature({ ...signed.signature, ...patch } as Signature),
    ).toThrow();
  await expect(
    recoverSigner(
      prepared.digest,
      signed.signature,
      ('0x' + '1'.repeat(40)) as `0x${string}`,
    ),
  ).rejects.toMatchObject({ kind: 'invalid-signature' });
  await expect(
    recoverSigner(
      prepared.digest,
      { r: 5n, s: 1n, yParity: false },
      prepared.request.ethereumAddress,
    ),
  ).rejects.toMatchObject({ kind: 'invalid-signature' });
  expect(() =>
    encodeSigned({
      ...signed,
      recoveredAddress: ('0x' + '1'.repeat(40)) as `0x${string}`,
    }),
  ).toThrow();
});
test('error shape retains causes and never accepts spoofed SDK errors', () => {
  const owned = failure('invalid-input', 'query', 'invalid');
  expect(providerFailure(owned, 'sign')).toBe(owned);
  for (const [code, kind] of [
    [4001, 'user-rejected'],
    [4200, 'unsupported-method'],
    [-32601, 'unsupported-method'],
    [4900, 'disconnected'],
    [4901, 'disconnected'],
    [999, 'provider'],
  ] as const)
    expect(providerFailure({ code }, 'sign')).toMatchObject({
      kind,
      cause: { code },
    });
  for (const cause of [
    null,
    'failure',
    new Error('ordinary'),
    Object.assign(new Error('spoof'), { name: 'RegistryClientError' }),
  ])
    expect(providerFailure(cause, 'query')).toMatchObject({
      kind: 'provider',
      cause,
    });
  expect(confirmationUnavailable(word(5n), 'timeout')).toMatchObject({
    kind: 'confirmation-unavailable',
    stage: 'wait',
    transactionHash: word(5n),
    cause: 'timeout',
  });
});

test('every signed message/domain field and ordered type tuple is reconstructed before authorization', () => {
  for (const fixture of fixtures) {
    const { prepared } = fixtureState(fixture);
    for (const section of ['message', 'domain'] as const) {
      for (const key of Object.keys(prepared.typedData[section])) {
        const copy = structuredClone(prepared);
        const fields = copy.typedData[section] as unknown as Record<
          string,
          unknown
        >;
        fields[key] = 'tampered';
        expect(() => authenticatePrepared(copy)).toThrow();
      }
    }
    for (const key of Object.keys(prepared.typedData.types)) {
      const copy = structuredClone(prepared);
      const fields = copy.typedData.types as unknown as Record<string, unknown>;
      fields[key] = [{ name: 'ethereumAddress', type: 'bytes32' }];
      expect(() => authenticatePrepared(copy)).toThrow();
    }
  }
});

test('owned confirmation errors preserve the known hash and original cause through provider boundaries', () => {
  const cause = new Error('Wait interrupted');
  const error = confirmationUnavailable(word(66n), cause);
  expect(providerFailure(error, 'validate')).toBe(error);
  expect(error).toMatchObject({
    kind: 'confirmation-unavailable',
    stage: 'wait',
    transactionHash: word(66n),
    cause,
  });
});
