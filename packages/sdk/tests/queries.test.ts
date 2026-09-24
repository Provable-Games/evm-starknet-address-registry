import { readFileSync } from 'node:fs';
import { expect, test, vi } from 'vitest';
import {
  createRegistryReader,
  compareLinkedAddresses,
} from '../src/queries.js';
import type { RegistryTransport } from '../src/queries.js';
import {
  ethereumAddress,
  word,
  ZERO_ACCOUNT,
  FELT_PRIME,
} from '../src/addresses.js';
import { fixtureState, fixtures, firstFixture } from './fixtures.js';
const deployments = (
  JSON.parse(
    readFileSync(
      new URL('../../../protocol/vectors.json', import.meta.url),
      'utf8',
    ),
  ) as {
    deployments: {
      account_label: string;
      account_chain: string;
      get_signing_domain_return: string[];
      get_version_return: string[];
    }[];
  }
).deployments;
function transportMock(fixture = firstFixture()) {
  const state = fixtureState(fixture);
  const discovery = deployments.find(
    (entry) =>
      entry.account_label === fixture.account_label &&
      entry.account_chain ===
        (state.deployment.ethereumChainId === 1n ? 'SN_MAIN' : 'SN_SEPOLIA'),
  );
  if (!discovery) throw new Error('Missing independent discovery fixture');
  const handlers: Record<
    string,
    (calldata: readonly string[]) => readonly string[]
  > = {
    get_signing_domain: () => discovery.get_signing_domain_return,
    get_version: () => discovery.get_version_return,
    get_starknet_address: () => [
      BigInt(state.snapshot.currentAccountAddress).toString(),
    ],
    get_ethereum_nonce: () => ['5', '1'],
    get_recipient_nonce: () => ['7', '2'],
    get_ethereum_address_count: () => ['0'],
    get_ethereum_addresses: () => ['0'],
    is_associated: () => ['0'],
  };
  const transport = {
    getBlock: vi.fn<RegistryTransport['getBlock']>(async () => {
      await Promise.resolve();
      return {
        blockHash: state.snapshot.blockHash,
        timestamp: state.snapshot.timestamp,
      };
    }),
    getChainId: vi.fn<RegistryTransport['getChainId']>(async () => {
      await Promise.resolve();
      return state.deployment.accountChainId;
    }),
    getClassHash: vi.fn<RegistryTransport['getClassHash']>(async () => {
      await Promise.resolve();
      return state.deployment.classHash;
    }),
    call: vi.fn<RegistryTransport['call']>(async (call, block) => {
      await Promise.resolve();
      expect(block).toBe(state.snapshot.blockHash);
      expect(call.contractAddress).toBe(state.deployment.registryAddress);
      const handler = handlers[call.entrypoint];
      if (!handler) throw new Error('Unknown mocked entrypoint');
      return handler(call.calldata);
    }),
  };
  return {
    ...state,
    transport,
    handlers,
    reader: createRegistryReader(state.deployment, transport),
  };
}
for (const fixture of fixtures)
  test(`authenticates complete independent discovery: ${fixture.id}`, async () => {
    const m = transportMock(fixture);
    expect(await m.reader.getSigningDomain(m.snapshot.blockHash)).toEqual(
      m.snapshot.signingDomain,
    );
    expect(await m.reader.getVersion(m.snapshot.blockHash)).toBe(49n);
  });
test('all reads preserve native results, full widths and the concrete block', async () => {
  const m = transportMock(),
    e = m.snapshot.ethereumAddress,
    a = m.snapshot.accountAddress,
    b = m.snapshot.blockHash;
  expect(await m.reader.getStarknetAddress(e, b)).toBe(ZERO_ACCOUNT);
  expect(await m.reader.getEthereumNonce(e, b)).toBe((1n << 128n) + 5n);
  expect(await m.reader.getRecipientNonce(a, e, b)).toBe((2n << 128n) + 7n);
  expect(await m.reader.isAssociated(e, a, b)).toBe(false);
  m.handlers.is_associated = () => ['1'];
  expect(await m.reader.isAssociated(e, a, b)).toBe(true);
  expect(await m.reader.getEthereumAddressCount(a, b)).toBe(0n);
  expect(await m.reader.getEthereumAddresses(a, 0n, 1n, b)).toEqual([]);
  expect(await m.reader.listAllEthereumAddresses(a, b)).toMatchObject({
    blockHash: b,
    ethereumAddresses: [],
  });
  expect(await m.reader.snapshot(m.deployment, e, a)).toMatchObject({
    blockHash: b,
    ethereumNonce: (1n << 128n) + 5n,
  });
  expect(await m.reader.snapshot(m.deployment, e, a, b)).toMatchObject({
    blockHash: b,
  });
  m.handlers.get_ethereum_address_count = () => ['205'];
  m.handlers.get_ethereum_addresses = (args) => {
    const offset = BigInt(args[1] ?? '0');
    const count = offset === 200n ? 5 : 100;
    return [
      String(count),
      ...Array.from({ length: count }, (_, index) =>
        (offset + BigInt(index) + 1n).toString(),
      ),
    ];
  };
  const listed = await m.reader.listAllEthereumAddresses(a, b);
  expect(listed.ethereumAddresses).toHaveLength(205);
  expect(listed.ethereumAddresses[204]).toBe(
    '0x' + (205).toString(16).padStart(40, '0'),
  );
  const compared = compareLinkedAddresses(
    {
      ...listed,
      ethereumAddresses: [...listed.ethereumAddresses, e, ethereumAddress(e)],
    },
    [e, e, ('0x' + 'f'.repeat(40)) as `0x${string}`],
  );
  expect(compared.matches).toEqual([e]);
  expect(compared.normalizedAllowedAddresses).toHaveLength(2);
  expect(compared.snapshot.blockHash).toBe(b);
  expect(() => compareLinkedAddresses(listed, ['0x1'])).toThrow();
});
test('chain/class/domain/version spoofing rejects authenticated reads', async () => {
  for (const mode of [
    'chain',
    'class',
    'class-range',
    'domain',
    'domain-extra',
    'version',
    'version-extra',
    'failure',
  ]) {
    const m = transportMock();
    if (mode === 'chain')
      vi.mocked(m.transport.getChainId).mockResolvedValue(1n);
    else if (mode === 'class')
      vi.mocked(m.transport.getClassHash).mockResolvedValue(word(999n));
    else if (mode === 'class-range')
      vi.mocked(m.transport.getClassHash).mockResolvedValue(word(FELT_PRIME));
    else if (mode === 'domain') m.handlers.get_signing_domain = () => ['1'];
    else if (mode === 'domain-extra')
      m.handlers.get_signing_domain = () => [
        ...(deployments[0]?.get_signing_domain_return ?? []),
        '0',
      ];
    else if (mode === 'version') m.handlers.get_version = () => ['1'];
    else if (mode === 'version-extra')
      m.handlers.get_version = () => ['49', '0'];
    else
      vi.mocked(m.transport.getClassHash).mockRejectedValue({
        message: 'offline',
      });
    await expect(
      m.reader.getStarknetAddress(
        m.snapshot.ethereumAddress,
        m.snapshot.blockHash,
      ),
    ).rejects.toBeInstanceOf(Error);
  }
});
test('malformed/failed RPC, incomplete pages and block mismatch never become empty success', async () => {
  const m = transportMock(),
    e = m.snapshot.ethereumAddress,
    a = m.snapshot.accountAddress,
    b = m.snapshot.blockHash;
  for (const values of [
    [],
    ['1', '2'],
    ['01'],
    [FELT_PRIME.toString()],
    [(1n << 251n).toString()],
  ]) {
    m.handlers.get_starknet_address = () => values;
    await expect(m.reader.getStarknetAddress(e, b)).rejects.toThrow();
  }
  vi.mocked(m.transport.call).mockResolvedValueOnce(
    null as unknown as string[],
  );
  await expect(m.reader.getVersion(b)).rejects.toThrow();
  m.handlers.get_ethereum_nonce = () => ['1'];
  await expect(m.reader.getEthereumNonce(e, b)).rejects.toThrow();
  m.handlers.get_ethereum_nonce = () => [(1n << 128n).toString(), '0'];
  await expect(m.reader.getEthereumNonce(e, b)).rejects.toThrow();
  m.handlers.is_associated = () => ['2'];
  await expect(m.reader.isAssociated(e, a, b)).rejects.toThrow();
  m.handlers.get_ethereum_address_count = () => [(1n << 64n).toString()];
  await expect(m.reader.getEthereumAddressCount(a, b)).rejects.toThrow();
  for (const limit of [0n, 101n, 1n << 32n])
    await expect(
      m.reader.getEthereumAddresses(a, 0n, limit, b),
    ).rejects.toThrow();
  await expect(
    m.reader.getEthereumAddresses(a, 1n << 64n, 1n, b),
  ).rejects.toThrow();
  for (const values of [
    [],
    ['1'],
    ['2', '1', '2'],
    ['1', '0'],
    ['1', (1n << 160n).toString()],
  ]) {
    m.handlers.get_ethereum_addresses = () => values;
    await expect(m.reader.getEthereumAddresses(a, 0n, 1n, b)).rejects.toThrow();
  }
  m.handlers.get_ethereum_address_count = () => ['2'];
  m.handlers.get_ethereum_addresses = () => ['1', '1'];
  await expect(m.reader.listAllEthereumAddresses(a, b)).rejects.toThrow();
  m.handlers.get_ethereum_addresses = () => ['2', '1', '1'];
  await expect(m.reader.listAllEthereumAddresses(a, b)).rejects.toThrow();
  const cause = Object.assign(new Error('page RPC failed'), { code: -999 });
  m.handlers.get_ethereum_addresses = () => {
    throw cause;
  };
  await expect(m.reader.listAllEthereumAddresses(a, b)).rejects.toMatchObject({
    cause,
  });
  await expect(
    m.reader.snapshot({ ...m.deployment, classHash: word(999n) }, e, a),
  ).rejects.toThrow();
  vi.mocked(m.transport.getBlock).mockResolvedValueOnce({
    blockHash: word(999n),
    timestamp: 1n,
  });
  await expect(m.reader.snapshot(m.deployment, e, a, b)).rejects.toThrow();
  vi.mocked(m.transport.getBlock).mockRejectedValueOnce(cause);
  await expect(m.reader.snapshot(m.deployment, e, a)).rejects.toMatchObject({
    cause,
  });
});

test('trusted tuple comparison is by canonical field values, independent of object key order', async () => {
  const m = transportMock();
  const reversed = Object.fromEntries(
    Object.entries(m.deployment).reverse(),
  ) as unknown as typeof m.deployment;
  await expect(
    m.reader.snapshot(
      reversed,
      m.snapshot.ethereumAddress,
      m.snapshot.accountAddress,
    ),
  ).resolves.toMatchObject({ blockHash: m.snapshot.blockHash });
});

test('same-block authentication shares only in-flight checks and retries every later operation', async () => {
  const m = transportMock(),
    b = m.snapshot.blockHash;
  await Promise.all([m.reader.getSigningDomain(b), m.reader.getVersion(b)]);
  expect(m.transport.getChainId).toHaveBeenCalledTimes(1);
  expect(m.transport.getClassHash).toHaveBeenCalledTimes(1);
  await m.reader.getVersion(b);
  expect(m.transport.getChainId).toHaveBeenCalledTimes(2);
  m.transport.getChainId.mockResolvedValue(0n);
  const failed = await Promise.allSettled([
    m.reader.getSigningDomain(b),
    m.reader.getVersion(b),
  ]);
  expect(failed.map((result) => result.status)).toEqual([
    'rejected',
    'rejected',
  ]);
  expect(m.transport.getChainId).toHaveBeenCalledTimes(3);
  m.transport.getChainId.mockResolvedValue(m.deployment.accountChainId);
  await m.reader.getVersion(b);
  expect(m.transport.getChainId).toHaveBeenCalledTimes(4);
  const other = word(987n);
  m.transport.call.mockImplementation(async (call) => {
    await Promise.resolve();
    const handler = m.handlers[call.entrypoint];
    if (!handler) throw new Error('Missing handler');
    return handler(call.calldata);
  });
  await Promise.all([m.reader.getVersion(b), m.reader.getVersion(other)]);
  expect(m.transport.getChainId).toHaveBeenCalledTimes(6);
  expect(m.transport.getClassHash).toHaveBeenLastCalledWith(
    m.deployment.registryAddress,
    other,
  );
});

test('interleaved blocks share each in-flight authentication and clear both entries', async () => {
  const m = transportMock(),
    a = m.snapshot.blockHash,
    b = word(987n);
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  m.transport.getChainId.mockImplementation(async () => {
    await pending;
    return m.deployment.accountChainId;
  });
  m.transport.call.mockImplementation(async (call) => {
    await Promise.resolve();
    const handler = m.handlers[call.entrypoint];
    if (!handler) throw new Error('Missing handler');
    return handler(call.calldata);
  });
  const reads = [
    m.reader.getVersion(a),
    m.reader.getVersion(b),
    m.reader.getSigningDomain(a),
  ];
  expect(m.transport.getChainId).toHaveBeenCalledTimes(2);
  release();
  await Promise.all(reads);
  await m.reader.getVersion(a);
  expect(m.transport.getChainId).toHaveBeenCalledTimes(3);
});

test('enumeration budgets bound work before any page and preserve explicit zero/boundary semantics', async () => {
  for (const [count, maximum, accepted] of [
    [0n, 0n, true],
    [1n, 0n, false],
    [100n, 100n, true],
    [101n, 100n, false],
    [10_000n, undefined, true],
    [10_001n, undefined, false],
    [10_001n, 10_001n, true],
    [(1n << 64n) - 1n, undefined, false],
  ] as const) {
    const m = transportMock();
    m.handlers.get_ethereum_address_count = () => [String(count)];
    m.handlers.get_ethereum_addresses = (args) => {
      const offset = BigInt(args[1] ?? '0'),
        length = Number(count - offset < 100n ? count - offset : 100n);
      return [
        String(length),
        ...Array.from({ length }, (_, i) => String(offset + BigInt(i) + 1n)),
      ];
    };
    const result = m.reader.listAllEthereumAddresses(
      m.snapshot.accountAddress,
      m.snapshot.blockHash,
      maximum === undefined ? undefined : { maxAddresses: maximum },
    );
    if (accepted)
      expect((await result).ethereumAddresses).toHaveLength(Number(count));
    else await expect(result).rejects.toMatchObject({ kind: 'invalid-input' });
    const pages = m.transport.call.mock.calls.filter(
      ([call]) => call.entrypoint === 'get_ethereum_addresses',
    );
    expect(pages).toHaveLength(accepted ? Number((count + 99n) / 100n) : 0);
  }
  for (const maximum of [-1n, 1n << 64n, 1, undefined, '1']) {
    const m = transportMock();
    await expect(
      m.reader.listAllEthereumAddresses(
        m.snapshot.accountAddress,
        m.snapshot.blockHash,
        { maxAddresses: maximum as bigint },
      ),
    ).rejects.toMatchObject({ kind: 'invalid-input' });
    expect(m.transport.call).not.toHaveBeenCalled();
  }
});
test('duplicate reverse entries reject on the first offending page', async () => {
  for (const duplicatePage of [0n, 100n]) {
    const m = transportMock();
    m.handlers.get_ethereum_address_count = () => ['10000'];
    m.handlers.get_ethereum_addresses = (args) => {
      const offset = BigInt(args[1] ?? '0');
      return [
        '100',
        ...Array.from({ length: 100 }, (_, i) =>
          String(
            offset === duplicatePage && i === 99 ? 1n : offset + BigInt(i) + 1n,
          ),
        ),
      ];
    };
    await expect(
      m.reader.listAllEthereumAddresses(
        m.snapshot.accountAddress,
        m.snapshot.blockHash,
      ),
    ).rejects.toMatchObject({ kind: 'invalid-input' });
    expect(
      m.transport.call.mock.calls.filter(
        ([call]) => call.entrypoint === 'get_ethereum_addresses',
      ),
    ).toHaveLength(Number(duplicatePage / 100n) + 1);
  }
});

test('malformed enumeration option objects fail before RPC', async () => {
  for (const options of [null, 1, {}, [], { maxAddresses: 1n, extra: true }]) {
    const m = transportMock();
    await expect(
      m.reader.listAllEthereumAddresses(
        m.snapshot.accountAddress,
        m.snapshot.blockHash,
        options as unknown as { maxAddresses: bigint },
      ),
    ).rejects.toMatchObject({ kind: 'invalid-input' });
    expect(m.transport.call).not.toHaveBeenCalled();
  }
});

test('one enumeration authenticates once while later pages and enumerations reauthenticate', async () => {
  const m = transportMock(),
    a = m.snapshot.accountAddress,
    b = m.snapshot.blockHash;
  m.handlers.get_ethereum_address_count = () => ['201'];
  m.handlers.get_ethereum_addresses = (args) => {
    const offset = Number(args[1]);
    const values = Array.from({ length: Math.min(100, 201 - offset) }, (_, i) =>
      String(offset + i + 1),
    );
    return [String(values.length), ...values];
  };
  expect(
    (await m.reader.listAllEthereumAddresses(a, b)).ethereumAddresses,
  ).toHaveLength(201);
  expect(m.transport.getChainId).toHaveBeenCalledTimes(1);
  expect(m.transport.getClassHash).toHaveBeenCalledTimes(1);
  expect(m.transport.call.mock.calls.map(([call]) => call.entrypoint)).toEqual([
    'get_signing_domain',
    'get_version',
    'get_ethereum_address_count',
    'get_ethereum_addresses',
    'get_ethereum_addresses',
    'get_ethereum_addresses',
  ]);
  await m.reader.getEthereumAddresses(a, 0n, 100n, b);
  expect(m.transport.getChainId).toHaveBeenCalledTimes(2);
  await m.reader.listAllEthereumAddresses(a, b);
  expect(m.transport.getChainId).toHaveBeenCalledTimes(3);
  m.transport.getChainId.mockResolvedValue(0n);
  await expect(m.reader.listAllEthereumAddresses(a, b)).rejects.toMatchObject({
    kind: 'deployment-mismatch',
  });
});
