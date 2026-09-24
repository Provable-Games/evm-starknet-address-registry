import { expect, test, vi } from 'vitest';
import { createRegistryClient } from '../src/client.js';
import { signWithProvider } from '../src/adapters.js';
import { word, ZERO_ACCOUNT } from '../src/addresses.js';
import type {
  EthereumProvider,
  PreparedRequest,
  SignedRequest,
  TransactionReceipt,
} from '../src/protocol.js';
import {
  fixtures,
  unsignedFixtures,
  fixtureState,
  firstFixture,
  mocks,
} from './fixtures.js';
function wallet(fixture = firstFixture()) {
  const state = fixtureState(fixture);
  const listeners = new Map<string, (value: unknown) => void>();
  const provider = {
    request: vi.fn<EthereumProvider['request']>(async ({ method }) => {
      await Promise.resolve();
      if (method === 'eth_accounts')
        return [state.prepared.request.ethereumAddress];
      if (method === 'eth_chainId')
        return '0x' + state.deployment.ethereumChainId.toString(16);
      if (method === 'eth_signTypedData_v4') return fixture.signature.v_27_28;
      throw new Error('Unexpected mocked wallet method');
    }),
    on: vi.fn<EthereumProvider['on']>((event, listener) => {
      listeners.set(event, listener);
    }),
    removeListener: vi.fn<EthereumProvider['removeListener']>((event) => {
      listeners.delete(event);
    }),
  };
  return { provider, listeners };
}
for (const fixture of fixtures)
  test(`mock adapters: prepare/sign/validate/build/receipt for ${fixture.id}`, async () => {
    const m = mocks(fixture),
      client = createRegistryClient(m),
      w = wallet(fixture);
    const operation = m.prepared.operation;
    const prepared = await (
      operation === 'link'
        ? client.prepareLink.bind(client)
        : operation === 'move'
          ? client.prepareMove.bind(client)
          : client.prepareRevoke.bind(client)
    )(m.snapshot.ethereumAddress, m.prepared.request.deadline);
    expect(prepared).toEqual(m.prepared);
    const signed = await client.sign(prepared, w.provider);
    expect(signed).toEqual(m.signed);
    expect(w.listeners.size).toBe(0);
    const call = vi
      .mocked(w.provider.request)
      .mock.calls.find(([args]) => args.method === 'eth_signTypedData_v4');
    expect(call?.[0].params).toEqual([
      fixture.typed_data.message.ethereumAddress,
      JSON.stringify(fixture.typed_data),
    ]);
    await client.validate(signed);
    expect(client.encode(signed).calldata).toEqual(fixture.calldata.full);
    vi.mocked(m.account.wait).mockImplementation(async (hash) => {
      await Promise.resolve();
      vi.mocked(m.reader.getStarknetAddress).mockResolvedValue(
        operation === 'revoke' ? ZERO_ACCOUNT : m.snapshot.accountAddress,
      );
      vi.mocked(m.reader.getEthereumNonce).mockResolvedValue(
        m.snapshot.ethereumNonce + 1n,
      );
      vi.mocked(m.reader.getRecipientNonce).mockResolvedValue(
        m.snapshot.recipientNonce + 1n,
      );
      return {
        transactionHash: hash,
        blockHash: word(77n),
        status: 'succeeded',
      };
    });
    const result = await client.submit([signed]);
    expect(result.readback.status).toBe('matched');
    expect(result.receipt.status).toBe('succeeded');
    expect(m.account.simulate).toHaveBeenCalledExactlyOnceWith([
      client.encode(signed),
    ]);
    for (const args of vi.mocked(m.reader.getStarknetAddress).mock.calls)
      expect(args[1]).toBe(word(77n));
  });

test('revocation prepares and signs without native account access; submission needs a relay', async () => {
  const fixture = fixtures.find(
    (value) => value.typed_data.primaryType === 'RevokeAssociation',
  );
  if (!fixture) throw new Error('Missing revoke fixture');
  const m = mocks(fixture),
    w = wallet(fixture),
    client = createRegistryClient(m);
  m.account.identity.mockRejectedValue(
    new Error('No connected Starknet account'),
  );
  const prepared = await client.prepareRevoke(
    m.snapshot.ethereumAddress,
    m.prepared.request.deadline,
  );
  expect(m.reader.snapshot).toHaveBeenCalledWith(
    m.deployment,
    m.snapshot.ethereumAddress,
    m.deployment.registryAddress,
    undefined,
  );
  const signed = await client.sign(prepared, w.provider);
  await client.validate(signed);
  expect(signed.prepared.digest).toBe(m.prepared.digest);
  expect(m.account.identity).not.toHaveBeenCalled();
  await expect(client.submit([signed])).rejects.toMatchObject({
    kind: 'provider',
    stage: 'validate',
  });
  expect(m.account.execute).not.toHaveBeenCalled();
});
test('unknown confirmation, reverted execution, mismatch and unavailable readback stay distinct', async () => {
  for (const mode of [
    'timeout',
    'bad-hash',
    'bad-status',
    'bad-block',
    'reverted',
    'mismatch',
    'unavailable',
    'pair-mismatch',
    'nonce-mismatch',
  ]) {
    const m = mocks(),
      client = createRegistryClient(m),
      cause = new Error('RPC interrupted');
    if (mode === 'timeout') vi.mocked(m.account.wait).mockRejectedValue(cause);
    else if (mode === 'bad-hash')
      vi.mocked(m.account.wait).mockResolvedValue({
        transactionHash: word(2n),
        blockHash: word(77n),
        status: 'succeeded',
      });
    else if (mode === 'bad-status')
      vi.mocked(m.account.wait).mockResolvedValue({
        transactionHash: word(66n),
        blockHash: word(77n),
        status: 'unknown',
      } as unknown as TransactionReceipt);
    else if (mode === 'bad-block')
      vi.mocked(m.account.wait).mockResolvedValue({
        transactionHash: word(66n),
        blockHash: '0x1',
        status: 'succeeded',
      });
    else if (mode === 'reverted')
      vi.mocked(m.account.wait).mockResolvedValue({
        transactionHash: word(66n),
        blockHash: word(77n),
        status: 'reverted',
      });
    else if (mode === 'unavailable')
      vi.mocked(m.reader.getStarknetAddress).mockRejectedValue(cause);
    else if (mode === 'pair-mismatch' || mode === 'nonce-mismatch') {
      vi.mocked(m.reader.getStarknetAddress).mockResolvedValue(
        m.snapshot.accountAddress,
      );
      vi.mocked(m.reader.getEthereumNonce).mockResolvedValue(
        mode === 'nonce-mismatch' ? 99n : 1n,
      );
    }
    const result = client.submit([m.signed]);
    if (['timeout', 'bad-hash', 'bad-status', 'bad-block'].includes(mode))
      await expect(result).rejects.toMatchObject({
        kind: 'confirmation-unavailable',
        stage: 'wait',
        transactionHash: word(66n),
      });
    else if (mode === 'reverted')
      await expect(result).rejects.toMatchObject({
        kind: 'execution-reverted',
        stage: 'wait',
      });
    else {
      const confirmed = await result;
      expect(confirmed.receipt.transactionHash).toBe(word(66n));
      expect(confirmed.readback.blockHash).toBe(word(77n));
      expect(confirmed.readback.status).toBe(
        mode === 'unavailable' ? 'unavailable' : 'mismatch',
      );
    }
    expect(m.account.execute).toHaveBeenCalledTimes(1);
  }
});
test('unsigned call builders are pure and unlink/cancel obey distinct mapping/nonces', async () => {
  for (const cancel of [true, false]) {
    const m = mocks(),
      client = createRegistryClient(m),
      ethereum = m.snapshot.ethereumAddress;
    if (!cancel)
      vi.mocked(m.reader.snapshot).mockResolvedValue({
        ...m.snapshot,
        currentAccountAddress: m.snapshot.accountAddress,
      });
    const call = cancel
      ? client.buildInvalidatePendingIncomingCall(ethereum)
      : client.buildUnlinkCall(ethereum);
    expect(call.entrypoint).toBe(
      cancel ? 'invalidate_pending_incoming' : 'unlink',
    );
    expect(m.account.execute).not.toHaveBeenCalled();
    vi.mocked(m.account.wait).mockImplementation(async (hash) => {
      await Promise.resolve();
      vi.mocked(m.reader.getEthereumNonce).mockResolvedValue(cancel ? 0n : 1n);
      vi.mocked(m.reader.getRecipientNonce).mockResolvedValue(1n);
      return {
        transactionHash: hash,
        blockHash: word(77n),
        status: 'succeeded',
      };
    });
    expect(
      (
        await (cancel
          ? client.invalidatePendingIncoming(ethereum)
          : client.unlink(ethereum))
      ).readback.status,
    ).toBe('matched');
  }
  const m = mocks(),
    client = createRegistryClient(m);
  await expect(client.unlink(m.snapshot.ethereumAddress)).rejects.toMatchObject(
    { kind: 'stale-request' },
  );
  expect(() =>
    client.buildUnlinkCall(('0x' + '0'.repeat(40)) as `0x${string}`),
  ).toThrow();
  await expect(client.submit([])).rejects.toThrow();
  await expect(client.submit([m.signed, m.signed])).rejects.toThrow();
});
test('prepare and validation reject altered deployment, identity, signed fields, state, and nonce overflow', async () => {
  for (const mode of [
    'chain',
    'identity-rpc',
    'identity-zero',
    'prepare-account-race',
    'snapshot-id',
    'snapshot-rpc',
    'class',
    'configured',
    'destination',
    'expired',
    'eth-nonce',
    'recipient-nonce',
    'mapping',
    'recovered',
    'digest',
    'validate-race',
    'overflow',
  ]) {
    const m = mocks(),
      client = createRegistryClient(m);
    let signed: SignedRequest = m.signed;
    if (mode === 'chain')
      vi.mocked(m.account.identity).mockResolvedValue({
        address: m.snapshot.accountAddress,
        chainId: 1n,
      });
    else if (mode === 'identity-rpc')
      vi.mocked(m.account.identity).mockRejectedValue({ code: 4900 });
    else if (mode === 'identity-zero')
      vi.mocked(m.account.identity).mockResolvedValue({
        address: ZERO_ACCOUNT,
        chainId: m.deployment.accountChainId,
      });
    else if (mode === 'prepare-account-race' || mode === 'validate-race')
      vi.mocked(m.account.identity)
        .mockResolvedValueOnce({
          address: m.snapshot.accountAddress,
          chainId: m.deployment.accountChainId,
        })
        .mockResolvedValue({
          address: word(999n),
          chainId: m.deployment.accountChainId,
        });
    else if (mode === 'snapshot-id')
      vi.mocked(m.reader.snapshot).mockResolvedValue({
        ...m.snapshot,
        accountAddress: word(999n),
      });
    else if (mode === 'snapshot-rpc')
      vi.mocked(m.reader.snapshot).mockRejectedValue({ code: -1 });
    else if (mode === 'class')
      vi.mocked(m.reader.snapshot).mockResolvedValue({
        ...m.snapshot,
        classHash: word(999n),
      });
    else if (mode === 'configured')
      signed = {
        ...signed,
        prepared: {
          ...signed.prepared,
          deployment: { ...signed.prepared.deployment, classHash: word(999n) },
          snapshot: { ...signed.prepared.snapshot, classHash: word(999n) },
        },
      };
    else if (mode === 'destination')
      vi.mocked(m.account.identity).mockResolvedValue({
        address: word(999n),
        chainId: m.deployment.accountChainId,
      });
    else if (mode === 'expired')
      vi.mocked(m.reader.snapshot).mockResolvedValue({
        ...m.snapshot,
        timestamp: m.prepared.request.deadline + 1n,
      });
    else if (mode === 'eth-nonce' || mode === 'overflow')
      vi.mocked(m.reader.snapshot).mockResolvedValue({
        ...m.snapshot,
        ethereumNonce: mode === 'overflow' ? 1n << 256n : 1n,
      });
    else if (mode === 'recipient-nonce')
      vi.mocked(m.reader.snapshot).mockResolvedValue({
        ...m.snapshot,
        recipientNonce: 1n,
      });
    else if (mode === 'mapping')
      vi.mocked(m.reader.snapshot).mockResolvedValue({
        ...m.snapshot,
        currentAccountAddress: word(999n),
      });
    else if (mode === 'recovered')
      signed = {
        ...signed,
        recoveredAddress: ('0x' + '1'.repeat(40)) as `0x${string}`,
      };
    else if (mode === 'digest')
      signed = {
        ...signed,
        prepared: { ...signed.prepared, digest: word(1n) },
      };
    await expect(
      mode === 'prepare-account-race'
        ? client.prepareLink(m.snapshot.ethereumAddress)
        : client.validate(signed),
    ).rejects.toThrow();
    expect(m.account.execute).not.toHaveBeenCalled();
  }
});
test('simulation/execution failures and account changes do not fabricate confirmations', async () => {
  for (const mode of [
    'simulation',
    'execution',
    'bad-hash',
    'post-sim-race',
    'pre-sim-race',
    'unsigned-race',
  ]) {
    const m = mocks(),
      client = createRegistryClient(m);
    if (mode === 'simulation')
      vi.mocked(m.account.simulate).mockRejectedValue('simulation failed');
    else if (mode === 'execution')
      vi.mocked(m.account.execute).mockRejectedValue({ code: 4900 });
    else if (mode === 'bad-hash')
      vi.mocked(m.account.execute).mockResolvedValue('0x1');
    else if (mode === 'post-sim-race')
      vi.mocked(m.account.simulate).mockImplementation(async () => {
        await Promise.resolve();
        vi.mocked(m.account.identity).mockResolvedValue({
          address: word(999n),
          chainId: m.deployment.accountChainId,
        });
      });
    else {
      let calls = 0;
      vi.mocked(m.account.identity).mockImplementation(async () => {
        await Promise.resolve();
        return {
          address:
            ++calls >= (mode === 'unsigned-race' ? 2 : 4)
              ? word(999n)
              : m.snapshot.accountAddress,
          chainId: m.deployment.accountChainId,
        };
      });
    }
    await expect(
      mode === 'unsigned-race'
        ? client.invalidatePendingIncoming(m.snapshot.ethereumAddress)
        : client.submit([m.signed]),
    ).rejects.toThrow();
    expect(m.account.wait).not.toHaveBeenCalled();
  }
});
test('selected wallet failures, unchanged events, rejected/unsupported methods and late races', async () => {
  const { prepared } = fixtureState(firstFixture());
  for (const mode of [
    'accounts',
    'chain',
    'empty',
    'rejected',
    'unsupported',
    'bad-signature',
    'account-event',
    'chain-event',
    'disconnect',
    'unchanged',
  ]) {
    const w = wallet();
    if (mode === 'accounts')
      vi.mocked(w.provider.request).mockResolvedValueOnce([
        '0x' + '1'.repeat(40),
      ]);
    else if (mode === 'empty')
      vi.mocked(w.provider.request).mockResolvedValueOnce([]);
    else if (mode === 'chain')
      vi.mocked(w.provider.request)
        .mockResolvedValueOnce([prepared.request.ethereumAddress])
        .mockResolvedValueOnce('0x2');
    else if (mode === 'rejected' || mode === 'unsupported')
      vi.mocked(w.provider.request).mockRejectedValueOnce({
        code: mode === 'rejected' ? 4001 : 4200,
      });
    else {
      const original = w.provider.request;
      w.provider.request = vi.fn<EthereumProvider['request']>(async (args) => {
        await Promise.resolve();
        if (args.method !== 'eth_signTypedData_v4') return original(args);
        if (mode === 'bad-signature') return '0x00';
        if (mode === 'account-event')
          w.listeners.get('accountsChanged')?.(['0x' + '1'.repeat(40)]);
        if (mode === 'chain-event') w.listeners.get('chainChanged')?.('0x2');
        if (mode === 'disconnect')
          w.listeners.get('disconnect')?.({ code: 4900 });
        if (mode === 'unchanged') {
          w.listeners.get('accountsChanged')?.([
            prepared.request.ethereumAddress,
          ]);
          w.listeners.get('chainChanged')?.('0x1');
        }
        return firstFixture().signature.v_27_28;
      });
    }
    if (mode === 'unchanged')
      expect(await signWithProvider(prepared, w.provider)).toMatchObject({
        prepared,
      });
    else await expect(signWithProvider(prepared, w.provider)).rejects.toThrow();
    expect(w.listeners.size).toBe(0);
  }
});
test('abandoned active attempt cannot accept a late signature or invalidate completed requests', async () => {
  const m = mocks(),
    client = createRegistryClient(m),
    first = wallet();
  const completed = await client.sign(m.prepared, first.provider);
  let resolveSignature: (signature: string) => void = () => undefined;
  const pending = new Promise<string>((resolve) => {
    resolveSignature = resolve;
  });
  const next = wallet(),
    original = next.provider.request;
  next.provider.request = vi.fn<EthereumProvider['request']>((args) =>
    args.method === 'eth_signTypedData_v4' ? pending : original(args),
  );
  const attempt = client.sign(m.prepared, next.provider);
  await vi.waitFor(() => {
    expect(
      vi
        .mocked(next.provider.request)
        .mock.calls.some(([args]) => args.method === 'eth_signTypedData_v4'),
    ).toBe(true);
  });
  next.listeners.get('disconnect')?.('closed');
  await expect(attempt).rejects.toMatchObject({ kind: 'disconnected' });
  resolveSignature(firstFixture().signature.v_27_28);
  expect(completed).toEqual(m.signed);
  await client.validate(completed);
  expect(next.listeners.size).toBe(0);
  expect(() => {
    (completed.prepared as unknown as { digest: string }).digest = word(1n);
  }).toThrow();
});
test('invalid arbitrary prepared objects cannot reach selected-wallet requests', async () => {
  const m = mocks(),
    client = createRegistryClient(m),
    w = wallet();
  await expect(
    client.sign(
      { ...m.prepared, typedData: null } as unknown as PreparedRequest,
      w.provider,
    ),
  ).rejects.toThrow();
  expect(w.provider.request).not.toHaveBeenCalled();
});

test('account identity changing while Ethereum wallet is open invalidates only that attempt', async () => {
  const m = mocks(),
    client = createRegistryClient(m),
    w = wallet();
  const original = w.provider.request;
  w.provider.request = vi.fn<EthereumProvider['request']>((args) => {
    if (args.method === 'eth_signTypedData_v4')
      m.account.identity.mockResolvedValue({
        address: word(999n),
        chainId: m.deployment.accountChainId,
      });
    return original(args);
  });
  await expect(client.sign(m.prepared, w.provider)).rejects.toMatchObject({
    kind: 'account-changed',
    stage: 'sign',
  });
  expect(m.account.execute).not.toHaveBeenCalled();
});

test('independent two-wallet batch preserves both signed requests and submitted calldata', async () => {
  const { privateKeyToAccount } = await import('viem/accounts');
  const { prepareRequest } = await import('../src/typed-data.js');
  const { parseSignature } = await import('../src/signature.js');
  const { ethereumAddress } = await import('../src/addresses.js');
  const m = mocks(),
    client = createRegistryClient(m);
  const publicTestKey2 = privateKeyToAccount(word(2n));
  const secondPrepared = prepareRequest(
    m.deployment,
    { ...m.snapshot, ethereumAddress: ethereumAddress(publicTestKey2.address) },
    'link',
    m.prepared.request.deadline,
  );
  const second: SignedRequest = {
    prepared: secondPrepared,
    signature: parseSignature(
      await publicTestKey2.sign({ hash: secondPrepared.digest }),
    ),
    recoveredAddress: ethereumAddress(publicTestKey2.address),
  };
  const originalSnapshot = m.reader.snapshot.getMockImplementation();
  if (!originalSnapshot) throw new Error('Missing snapshot mock');
  let latestReads = 0;
  m.reader.snapshot.mockImplementation(
    async (deployment, ethereum, account, block) => {
      const state = await originalSnapshot(
        deployment,
        ethereum,
        account,
        block,
      );
      if (block === undefined) latestReads += 1;
      return { ...state, blockHash: block ?? word(100n + BigInt(latestReads)) };
    },
  );
  const submitted = await client.submit([m.signed, second]);
  expect(latestReads).toBe(1);
  expect(m.reader.snapshot.mock.calls.map((call) => call[3])).toEqual([
    undefined,
    word(101n),
  ]);
  m.reader.snapshot.mockImplementation(
    async (deployment, ethereum, account, block) => ({
      ...(await originalSnapshot(deployment, ethereum, account, block)),
      blockHash: block === undefined ? word(101n) : word(102n),
    }),
  );
  m.account.execute.mockClear();
  await expect(client.submit([m.signed, second])).rejects.toMatchObject({
    kind: 'invalid-input',
  });
  expect(m.account.execute).not.toHaveBeenCalled();
  m.reader.snapshot.mockImplementation(originalSnapshot);
  await client.submit([m.signed, second]);

  expect(m.account.execute).toHaveBeenCalledExactlyOnceWith([
    client.encode(m.signed),
    client.encode(second),
  ]);
  expect(submitted.receipt.transactionHash).toBe(word(66n));
  expect(submitted.readback.status).toBe('mismatch');
  expect(m.signed.prepared.request.ethereumAddress).not.toBe(
    second.prepared.request.ethereumAddress,
  );
});

test('current maximum nonce overflow rejects before account execution', async () => {
  const { privateKeyToAccount } = await import('viem/accounts');
  const { prepareRequest } = await import('../src/typed-data.js');
  const { parseSignature } = await import('../src/signature.js');
  for (const field of ['ethereumNonce', 'recipientNonce'] as const) {
    const m = mocks(),
      client = createRegistryClient(m),
      snapshot = { ...m.snapshot, [field]: (1n << 256n) - 1n };
    m.reader.snapshot.mockResolvedValue(snapshot);
    const prepared = prepareRequest(
      m.deployment,
      snapshot,
      'link',
      m.prepared.request.deadline,
    );
    const signature = parseSignature(
      await privateKeyToAccount(word(1n)).sign({ hash: prepared.digest }),
    );
    await expect(
      client.submit([
        {
          prepared,
          signature,
          recoveredAddress: prepared.request.ethereumAddress,
        },
      ]),
    ).rejects.toThrow();
    expect(m.account.execute).not.toHaveBeenCalled();
  }
  const m = mocks(),
    client = createRegistryClient(m);
  m.reader.snapshot.mockResolvedValue({
    ...m.snapshot,
    recipientNonce: (1n << 256n) - 1n,
  });
  await expect(
    client.invalidatePendingIncoming(m.snapshot.ethereumAddress),
  ).rejects.toThrow();
  expect(m.account.execute).not.toHaveBeenCalled();
});

test('signed revocation can be relayed by a different account without changing signed fields', async () => {
  const fixture = fixtures.find(
    (value) => value.typed_data.primaryType === 'RevokeAssociation',
  );
  if (!fixture) throw new Error('Missing revoke fixture');
  const m = mocks(fixture),
    client = createRegistryClient(m);
  m.account.identity.mockResolvedValue({
    address: word(999n),
    chainId: m.deployment.accountChainId,
  });
  const result = await client.submit([m.signed]);
  expect(result.receipt.status).toBe('succeeded');
  expect(m.account.execute).toHaveBeenCalledExactlyOnceWith([
    client.encode(m.signed),
  ]);
});

test('move readback preserves distinct old/destination pair nonces in receipt block', async () => {
  const fixture = fixtures.find(
    (value) => value.typed_data.primaryType === 'MoveAddress',
  );
  if (!fixture) throw new Error('Missing move fixture');
  const m = mocks(fixture),
    client = createRegistryClient(m),
    old = m.snapshot.currentAccountAddress;
  m.reader.getRecipientNonce.mockImplementation((account) =>
    Promise.resolve(account === old ? 100n : m.snapshot.recipientNonce),
  );
  m.account.wait.mockImplementation((hash) => {
    m.reader.getStarknetAddress.mockResolvedValue(m.snapshot.accountAddress);
    m.reader.getEthereumNonce.mockResolvedValue(m.snapshot.ethereumNonce + 1n);
    m.reader.getRecipientNonce.mockImplementation((account) =>
      Promise.resolve(account === old ? 101n : m.snapshot.recipientNonce + 1n),
    );
    return Promise.resolve({
      transactionHash: hash,
      blockHash: word(77n),
      status: 'succeeded',
    });
  });
  const result = await client.submit([m.signed]);
  expect(result.readback).toMatchObject({
    status: 'matched',
    blockHash: word(77n),
    observations: [
      {
        recipientNonces: [
          { accountAddress: old, nonce: 101n },
          {
            accountAddress: m.snapshot.accountAddress,
            nonce: m.snapshot.recipientNonce + 1n,
          },
        ],
      },
    ],
  });
});

test('cancelled deferred selection never opens a signing prompt after accounts return', async () => {
  for (const deferredMethod of ['eth_accounts', 'eth_chainId']) {
    const m = mocks(),
      client = createRegistryClient(m),
      w = wallet();
    let resolveRead!: (value: unknown) => void;
    const deferred = new Promise<unknown>((resolve) => {
      resolveRead = resolve;
    });
    const original = w.provider.request;
    w.provider.request = vi.fn<EthereumProvider['request']>((args) =>
      args.method === deferredMethod ? deferred : original(args),
    );
    const attempt = client.sign(m.prepared, w.provider);
    await vi.waitFor(() => {
      expect(
        w.provider.request.mock.calls.some(
          ([args]) => args.method === deferredMethod,
        ),
      ).toBe(true);
    });
    w.listeners.get('accountsChanged')?.(['0x' + '1'.repeat(40)]);
    w.listeners.get('chainChanged')?.('0x2');
    w.listeners.get('accountsChanged')?.([m.snapshot.ethereumAddress]);
    w.listeners.get('chainChanged')?.('0x1');
    await expect(attempt).rejects.toMatchObject({ kind: 'account-changed' });
    resolveRead(
      deferredMethod === 'eth_accounts' ? [m.snapshot.ethereumAddress] : '0x1',
    );
    await new Promise<void>((resolve) => {
      setImmediate(resolve);
    });
    expect(
      w.provider.request.mock.calls.some(
        ([args]) => args.method === 'eth_signTypedData_v4',
      ),
    ).toBe(false);
    expect(w.listeners.size).toBe(0);
  }
});

test('listener cleanup attempts all removals and preserves an original failed attempt', async () => {
  const { prepared } = fixtureState(firstFixture());
  for (const failed of [false, true]) {
    const w = wallet(),
      originalRemove = w.provider.removeListener,
      cleanup = new Error('unsubscribe failed');
    if (failed) w.provider.request.mockRejectedValueOnce({ code: 4001 });
    w.provider.removeListener = vi.fn<EthereumProvider['removeListener']>(
      (event, listener) => {
        originalRemove(event, listener);
        if (event === 'accountsChanged') throw cleanup;
      },
    );
    await expect(signWithProvider(prepared, w.provider)).rejects.toMatchObject({
      kind: failed ? 'user-rejected' : 'provider',
    });
    expect(w.provider.removeListener).toHaveBeenCalledTimes(3);
    expect(w.listeners.size).toBe(0);
  }
});

test('synchronous registration invalidation and partial registration failure remain handled', async () => {
  const { prepared } = fixtureState(firstFixture()),
    w = wallet(),
    original = w.provider.on;
  w.provider.on = vi.fn<EthereumProvider['on']>((event, listener) => {
    original(event, listener);
    if (event === 'accountsChanged') {
      listener([]);
      throw new Error('registration failed');
    }
  });
  await expect(signWithProvider(prepared, w.provider)).rejects.toMatchObject({
    kind: 'provider',
  });
  expect(w.provider.request).not.toHaveBeenCalled();
  expect(w.listeners.size).toBe(0);
});

test('old-pair preparation failures are structured and receipt-block failures preserve success and cause', async () => {
  for (const operation of ['MoveAddress', 'RevokeAssociation'] as const) {
    const fixture = fixtures.find(
      (value) =>
        value.typed_data.primaryType === operation &&
        (value.typed_data.primaryType !== 'RevokeAssociation' ||
          value.typed_data.message.currentAccountAddress !== ZERO_ACCOUNT),
    );
    if (!fixture) throw new Error('Missing linked operation fixture');
    const cause = new Error('Pair nonce RPC interrupted');
    const before = mocks(fixture),
      beforeClient = createRegistryClient(before);
    before.reader.getRecipientNonce.mockRejectedValue(cause);
    await expect(beforeClient.submit([before.signed])).rejects.toMatchObject({
      kind: 'provider',
      stage: 'validate',
      cause,
    });
    expect(before.account.simulate).not.toHaveBeenCalled();
    expect(before.account.execute).not.toHaveBeenCalled();
    const after = mocks(fixture),
      afterClient = createRegistryClient(after);
    after.account.wait.mockImplementation((transactionHash) => {
      after.reader.getRecipientNonce.mockRejectedValue(cause);
      return Promise.resolve({
        transactionHash,
        blockHash: word(77n),
        status: 'succeeded',
      });
    });
    const result = await afterClient.submit([after.signed]);
    expect(result.receipt).toMatchObject({
      transactionHash: word(66n),
      status: 'succeeded',
    });
    expect(result.readback).toEqual({
      status: 'unavailable',
      blockHash: word(77n),
      cause,
    });
    expect(after.account.execute).toHaveBeenCalledTimes(1);
    expect(await after.reader.getVersion(word(77n))).toBe(49n);
  }
});

test('provider invalidation covers deferred client preflight and final identity validation', async () => {
  for (const boundary of ['initial-identity', 'snapshot', 'final-identity']) {
    for (const event of [
      'accountsChanged',
      'chainChanged',
      'disconnect',
    ] as const) {
      const m = mocks(),
        client = createRegistryClient(m),
        w = wallet();
      let release!: () => void;
      const pending = new Promise<void>((resolve) => {
        release = resolve;
      });
      let waiting = false;
      const originalIdentity = m.account.identity;
      const originalSnapshot = m.reader.snapshot;
      let identities = 0;
      m.account.identity = vi.fn(async () => {
        identities++;
        if (
          (boundary === 'initial-identity' && identities === 1) ||
          (boundary === 'final-identity' && identities === 4)
        ) {
          waiting = true;
          await pending;
        }
        return originalIdentity();
      });
      m.reader.snapshot = vi.fn(async (...args) => {
        if (boundary === 'snapshot') {
          waiting = true;
          await pending;
        }
        return originalSnapshot(...args);
      });
      const attempt = client.sign(m.prepared, w.provider);
      await vi.waitFor(() => {
        expect(waiting).toBe(true);
      });
      expect(w.listeners.size).toBe(3);
      if (event === 'accountsChanged') {
        w.listeners.get(event)?.(['0x' + '1'.repeat(40)]);
        w.listeners.get(event)?.([m.snapshot.ethereumAddress]);
      } else if (event === 'chainChanged') {
        w.listeners.get(event)?.('0x2');
        w.listeners.get(event)?.('0x1');
      } else {
        w.listeners.get(event)?.({ code: 4900 });
      }
      await expect(attempt).rejects.toMatchObject({
        kind:
          event === 'accountsChanged'
            ? 'account-changed'
            : event === 'chainChanged'
              ? 'chain-changed'
              : 'disconnected',
      });
      release();
      await new Promise<void>((resolve) => {
        setImmediate(resolve);
      });
      expect(
        w.provider.request.mock.calls.filter(
          ([args]) => args.method === 'eth_signTypedData_v4',
        ),
      ).toHaveLength(boundary === 'final-identity' ? 1 : 0);
      if (boundary === 'initial-identity')
        expect(m.reader.snapshot).not.toHaveBeenCalled();
      expect(w.listeners.size).toBe(0);
    }
  }
});

test('empty selected accounts are disconnected while malformed results are invalid input', async () => {
  for (const value of [[], null, {}, 'bad']) {
    const w = wallet();
    w.provider.request.mockResolvedValueOnce(value);
    await expect(
      signWithProvider(mocks().prepared, w.provider),
    ).rejects.toMatchObject({
      kind: Array.isArray(value) ? 'disconnected' : 'invalid-input',
      stage: Array.isArray(value) ? 'sign' : 'validate',
    });
  }
});

test('native attempts permanently cancel away/back transitions at every pending boundary', async () => {
  for (const boundary of [
    'identity',
    'snapshot',
    'sign',
    'simulate',
  ] as const) {
    for (const reason of [
      'account-changed',
      'chain-changed',
      'disconnected',
    ] as const) {
      const m = mocks(),
        w = wallet();
      let generation = 0n;
      let change!: Parameters<typeof m.account.subscribeChange>[0];
      const unsubscribe = vi.fn();
      m.account.generation.mockImplementation(() => generation);
      m.account.subscribeChange.mockImplementation((listener) => {
        change = listener;
        return unsubscribe;
      });
      let release!: () => void;
      let reached!: () => void;
      const pending = new Promise<void>((resolve) => {
        release = resolve;
      });
      const entered = new Promise<void>((resolve) => {
        reached = resolve;
      });
      if (boundary === 'identity')
        m.account.identity.mockImplementationOnce(async () => {
          reached();
          await pending;
          return {
            address: m.snapshot.accountAddress,
            chainId: m.deployment.accountChainId,
          };
        });
      if (boundary === 'snapshot')
        m.reader.snapshot.mockImplementationOnce(async () => {
          reached();
          await pending;
          return m.snapshot;
        });
      if (boundary === 'simulate')
        m.account.simulate.mockImplementationOnce(async () => {
          reached();
          await pending;
        });
      if (boundary === 'sign')
        w.provider.request.mockImplementation(async ({ method }) => {
          if (method === 'eth_accounts') return [m.snapshot.ethereumAddress];
          reached();
          await pending;
          return '0x' + m.deployment.ethereumChainId.toString(16);
        });
      const client = createRegistryClient(m);
      const result =
        boundary === 'sign'
          ? client.sign(m.prepared, w.provider)
          : boundary === 'simulate'
            ? client.submit([m.signed])
            : client.prepareLink(m.snapshot.ethereumAddress);
      const rejected = expect(result).rejects.toMatchObject({ kind: reason });
      await entered;
      generation += 1n;
      change(reason);
      generation += 1n;
      change(reason);
      await rejected; // Must reject before the stalled adapter settles.
      expect(unsubscribe).toHaveBeenCalledOnce();
      release();
      await new Promise<void>((resolve) => setImmediate(resolve));
      expect(m.account.execute).not.toHaveBeenCalled();
      expect(
        w.provider.request.mock.calls.some(
          ([args]) => args.method === 'eth_signTypedData_v4',
        ),
      ).toBe(false);
      expect(w.listeners.size).toBe(0);
    }
  }
});

test('native change and Ethereum selection completion in either same-turn order never open a signing prompt', async () => {
  for (const resolveFirst of [true, false]) {
    const m = mocks(),
      w = wallet();
    let change!: Parameters<typeof m.account.subscribeChange>[0];
    m.account.subscribeChange.mockImplementation((listener) => {
      change = listener;
      return vi.fn();
    });
    let release!: (value: unknown) => void;
    let reached!: () => void;
    const entered = new Promise<void>((resolve) => {
      reached = resolve;
    });
    w.provider.request.mockImplementation(async ({ method }) => {
      if (method === 'eth_accounts') return [m.snapshot.ethereumAddress];
      reached();
      return new Promise<unknown>((resolve) => {
        release = resolve;
      });
    });
    const result = createRegistryClient(m).sign(m.prepared, w.provider);
    const rejected = expect(result).rejects.toMatchObject({
      kind: 'account-changed',
    });
    await entered;
    if (resolveFirst) release('0x1');
    change('account-changed');
    if (!resolveFirst) release('0x1');
    await rejected;
    await new Promise<void>((resolve) => setImmediate(resolve));
    expect(w.provider.request.mock.calls.map(([args]) => args.method)).toEqual([
      'eth_accounts',
      'eth_chainId',
    ]);
  }
});

test('native generation guards silent transitions and adapter setup/cleanup errors', async () => {
  for (const mode of [
    'generation-throw',
    'bad-generation',
    'negative',
    'subscribe-throw',
    'synchronous',
    'generation-change',
    'cleanup',
    'failed-cleanup',
  ] as const) {
    const m = mocks(),
      cause = new Error(mode);
    const unsubscribe = vi.fn();
    m.account.subscribeChange.mockImplementation((listener) => {
      if (mode === 'subscribe-throw') throw cause;
      if (mode === 'synchronous') listener('disconnected');
      return unsubscribe;
    });
    if (mode === 'generation-throw')
      m.account.generation.mockImplementation(() => {
        throw cause;
      });
    if (mode === 'bad-generation')
      m.account.generation.mockReturnValue(1 as unknown as bigint);
    if (mode === 'negative') m.account.generation.mockReturnValue(-1n);
    if (mode === 'generation-change')
      m.account.identity.mockImplementationOnce(async () => {
        await Promise.resolve();
        m.account.generation.mockReturnValue(2n);
        return {
          address: m.snapshot.accountAddress,
          chainId: m.deployment.accountChainId,
        };
      });
    if (mode === 'cleanup' || mode === 'failed-cleanup')
      unsubscribe.mockImplementation(() => {
        throw cause;
      });
    if (mode === 'failed-cleanup') m.account.identity.mockRejectedValue(cause);
    await expect(
      createRegistryClient(m).prepareLink(m.snapshot.ethereumAddress),
    ).rejects.toMatchObject({
      kind:
        mode === 'synchronous'
          ? 'disconnected'
          : mode === 'generation-change'
            ? 'account-changed'
            : mode === 'bad-generation' || mode === 'negative'
              ? 'invalid-input'
              : 'provider',
    });
  }
});

test('execute invocation ends cancellation while preserving delayed transaction and confirmation outcomes', async () => {
  for (const inconclusive of [false, true]) {
    const m = mocks();
    let change!: Parameters<typeof m.account.subscribeChange>[0];
    const unsubscribe = vi.fn();
    m.account.subscribeChange.mockImplementation((listener) => {
      change = listener;
      return unsubscribe;
    });
    m.account.execute.mockImplementation(async () => {
      expect(unsubscribe).toHaveBeenCalledOnce();
      change('disconnected');
      m.account.generation.mockReturnValue(9n);
      await Promise.resolve();
      return word(66n);
    });
    if (inconclusive) m.account.wait.mockRejectedValue(new Error('offline'));
    const result = createRegistryClient(m).submit([m.signed]);
    if (inconclusive)
      await expect(result).rejects.toMatchObject({
        kind: 'confirmation-unavailable',
        transactionHash: word(66n),
      });
    else expect((await result).receipt.transactionHash).toBe(word(66n));
    expect(unsubscribe).toHaveBeenCalledOnce();
  }
});

test('native change during final unsubscription aborts execution and cleanup errors preserve cancellation', async () => {
  for (const mode of ['event', 'generation', 'throw'] as const) {
    const m = mocks();
    let change!: Parameters<typeof m.account.subscribeChange>[0];
    const stop = vi.fn(() => {
      if (mode === 'event') change('chain-changed');
      else if (mode === 'generation') m.account.generation.mockReturnValue(1n);
      else throw new Error('unsubscribe failed');
    });
    m.account.subscribeChange.mockImplementation((listener) => {
      change = listener;
      return stop;
    });
    await expect(
      createRegistryClient(m).submit([m.signed]),
    ).rejects.toMatchObject({
      kind:
        mode === 'event'
          ? 'chain-changed'
          : mode === 'generation'
            ? 'account-changed'
            : 'provider',
    });
    expect(m.account.execute).not.toHaveBeenCalled();
    expect(stop).toHaveBeenCalledOnce();
  }
});

test('native change during ordinary cleanup cannot return a prepared request', async () => {
  for (const mode of ['event', 'generation'] as const) {
    const m = mocks();
    let change!: Parameters<typeof m.account.subscribeChange>[0];
    const stop = vi.fn(() => {
      if (mode === 'event') change('disconnected');
      else m.account.generation.mockReturnValue(1n);
    });
    m.account.subscribeChange.mockImplementation((listener) => {
      change = listener;
      return stop;
    });
    await expect(
      createRegistryClient(m).prepareLink(m.snapshot.ethereumAddress),
    ).rejects.toMatchObject({
      kind: mode === 'event' ? 'disconnected' : 'account-changed',
    });
    expect(stop).toHaveBeenCalledOnce();
  }
});

test('native change before simulation retains its cancellation reason', async () => {
  const m = mocks();
  let identities = 0;
  let checksAfterFinalIdentity = 0;
  m.account.identity.mockImplementation(async () => {
    await Promise.resolve();
    identities += 1;
    return {
      address: m.snapshot.accountAddress,
      chainId: m.deployment.accountChainId,
    };
  });
  m.account.generation.mockImplementation(() => {
    if (identities >= 4) {
      checksAfterFinalIdentity += 1;
      return checksAfterFinalIdentity >= 2 ? 1n : 0n;
    }
    return 0n;
  });
  await expect(
    createRegistryClient(m).submit([m.signed]),
  ).rejects.toMatchObject({
    kind: 'account-changed',
    stage: 'validate',
  });
  expect(m.account.simulate).not.toHaveBeenCalled();
});

test('generation changes without an event during simulation retain account-change classification', async () => {
  const m = mocks();
  m.account.simulate.mockImplementation(async () => {
    await Promise.resolve();
    m.account.generation.mockReturnValue(2n);
  });
  await expect(
    createRegistryClient(m).submit([m.signed]),
  ).rejects.toMatchObject({ kind: 'account-changed' });
  expect(m.account.execute).not.toHaveBeenCalled();
});

for (const fixture of unsignedFixtures)
  test(`unsigned builder matches independent frozen calldata: ${fixture.id}`, () => {
    const m = mocks(),
      client = createRegistryClient(m);
    const ethereum =
      `0x${BigInt(fixture.calldata[0]).toString(16).padStart(40, '0')}` as const;
    const call =
      fixture.entrypoint === 'unlink'
        ? client.buildUnlinkCall(ethereum)
        : client.buildInvalidatePendingIncomingCall(ethereum);
    expect(call).toEqual({
      contractAddress: m.deployment.registryAddress,
      entrypoint: fixture.entrypoint,
      calldata: fixture.calldata,
    });
  });

test('unknown cyclic or missing snapshot fields reject before recursive request freezing', async () => {
  for (const mode of ['extra', 'cycle', 'missing'] as const) {
    const m = mocks(),
      client = createRegistryClient(m);
    const snapshot: Record<string, unknown> = { ...m.snapshot };
    if (mode === 'missing') delete snapshot.timestamp;
    else snapshot.extra = mode === 'cycle' ? snapshot : true;
    m.reader.snapshot.mockResolvedValue(
      snapshot as unknown as typeof m.snapshot,
    );
    await expect(
      client.prepareLink(m.snapshot.ethereumAddress),
    ).rejects.toMatchObject({ kind: 'invalid-input' });
    expect(() =>
      client.encode({
        ...m.signed,
        prepared: { ...m.prepared, snapshot } as unknown as PreparedRequest,
      }),
    ).toThrow(expect.objectContaining({ kind: 'invalid-input' }));
  }
});

test('malformed native change reasons cancel without throwing through the callback', async () => {
  for (const reason of [
    undefined,
    null,
    'registry-revert',
    'ACCOUNT_CHANGED',
    1,
    {},
    false,
  ]) {
    const m = mocks();
    let change!: Parameters<typeof m.account.subscribeChange>[0];
    m.account.subscribeChange.mockImplementation((listener) => {
      change = listener;
      return () => undefined;
    });
    let release!: () => void;
    let entered!: () => void;
    const ready = new Promise<void>((resolve) => {
      entered = resolve;
    });
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    m.account.simulate.mockImplementationOnce(async () => {
      entered();
      await pending;
    });
    const result = createRegistryClient(m).submit([m.signed]);
    await ready;
    expect(() => {
      change(reason as Parameters<typeof change>[0]);
    }).not.toThrow();
    change('account-changed');
    await expect(result).rejects.toMatchObject({
      kind: 'invalid-input',
      stage: 'validate',
    });
    release();
    await Promise.resolve();
    await Promise.resolve();
    expect(m.account.execute).not.toHaveBeenCalled();
  }
});
