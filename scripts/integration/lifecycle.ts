import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { privateKeyToAccount } from 'viem/accounts';
import { hashTypedData } from 'viem';
import {
  ABI_SHA256,
  PROTOCOL_REVISION,
  accountAddress,
  ethereumAddress,
  createRegistryClient,
  createRegistryReader,
  parseSignature,
  typedDigest,
  type EthereumProvider,
  type RegistryClient,
  type SignedRequest,
  type SubmissionResult,
  type TrustedDeployment,
} from '@provable-games/evm-starknet-address-registry';
import {
  loadAssociationPreview,
  type PreviewState,
} from '../../examples/client/association-preview.ts';
import {
  CHAIN_ID,
  fixedAccount,
  hex,
  localRpc,
  object,
  receipt,
  transport,
} from './transport.ts';

const manifestPath = process.argv[2];
assert(manifestPath, 'Pass the private localhost deployment manifest');
const manifest = object(
  JSON.parse(readFileSync(manifestPath, 'utf8')) as unknown,
);
assert.equal(typeof manifest.url, 'string');
const url = manifest.url as string;
const rpc = localRpc(url);
assert.equal(await rpc('starknet_specVersion'), '0.10.2');
assert.equal(BigInt(hex(await rpc('starknet_chainId'))), CHAIN_ID);
const deployed = object(manifest.deployed);
const registry = object(deployed.EthereumAddressAssociationRegistry);
const consumer = object(deployed.AssociationConsumer);
const forwarder = object(deployed.ConsumerForwarder);
const deployment: TrustedDeployment = {
  ethereumChainId: 11155111n,
  accountChainId: CHAIN_ID,
  registryAddress: accountAddress(hex(registry.contract_address)),
  classHash: hex(registry.class_hash),
  accountLabel: 'Local Registry',
  protocolRevision: PROTOCOL_REVISION,
  abiSha256: ABI_SHA256,
};
const nativeAccounts = await rpc('devnet_getPredeployedAccounts');
assert(Array.isArray(nativeAccounts) && nativeAccounts.length >= 3);
const fixed = nativeAccounts.map((raw: unknown) => {
  const value = object(raw);
  assert.equal(typeof value.address, 'string');
  assert.equal(typeof value.private_key, 'string');
  return fixedAccount(
    url,
    value.address as string,
    value.private_key as string,
  );
});
const first = fixed[0];
const second = fixed[1];
const third = fixed[2];
assert(first && second && third);
const reader = createRegistryReader(deployment, transport(rpc));
const clients = fixed.map(({ adapter }) =>
  createRegistryClient({ deployment, reader, account: adapter }),
);
const a = clients[0];
const b = clients[1];
const c = clients[2];
assert(a && b && c);
const wallets = [1n, 2n, 3n, 4n].map((key) =>
  privateKeyToAccount(`0x${key.toString(16).padStart(64, '0')}`),
);
function walletAt(index: number) {
  const value = wallets[index];
  assert(value);
  return value;
}
const wallet = walletAt(0),
  wallet2 = walletAt(1),
  wallet3 = walletAt(2),
  wallet4 = walletAt(3);
const e = ethereumAddress(wallet.address),
  e2 = ethereumAddress(wallet2.address),
  e3 = ethereumAddress(wallet3.address);
const accountA = accountAddress(hex(first.account.address));
function limbs(value: bigint): string[] {
  return [(value & ((1n << 128n) - 1n)).toString(), (value >> 128n).toString()];
}
const results: { name: string; result: unknown }[] = [];
function provider(
  key: ReturnType<typeof privateKeyToAccount>,
): EthereumProvider {
  return {
    async request({ method, params }) {
      if (method === 'eth_accounts') return [key.address];
      if (method === 'eth_chainId') return '0xaa36a7';
      assert.equal(method, 'eth_signTypedData_v4');
      assert(params && typeof params[1] === 'string');
      const payload = JSON.parse(params[1]) as Parameters<
        typeof key.signTypedData
      >[0];
      return key.signTypedData(payload);
    },
    on() {
      /* Disposable software key has immutable identity. */
    },
    removeListener() {
      /* No mutable provider or wallet UI is involved. */
    },
  };
}
async function sign(
  client: RegistryClient,
  operation: 'link' | 'move' | 'revoke',
  key: ReturnType<typeof privateKeyToAccount> = wallet,
): Promise<SignedRequest> {
  const address = ethereumAddress(key.address);
  const prepared = await (operation === 'link'
    ? client.prepareLink(address)
    : operation === 'move'
      ? client.prepareMove(address)
      : client.prepareRevoke(address));
  return client.sign(prepared, provider(key));
}
function matched(name: string, value: SubmissionResult): void {
  assert.equal(value.receipt.status, 'succeeded');
  assert.equal(value.readback.status, 'matched');
  assert.equal(value.receipt.blockHash, value.readback.blockHash);
  results.push({ name, result: value });
}
async function block() {
  return (await transport(rpc).getBlock()).blockHash;
}
async function rejected(
  name: string,
  action: () => Promise<unknown>,
  expected: string | { kind: string; stage: string },
): Promise<void> {
  let caught = false;
  try {
    await action();
  } catch (error) {
    caught = true;
    if (typeof expected === 'string')
      assert(
        String(error).includes(expected) ||
          String(error).includes(`0x${Buffer.from(expected).toString('hex')}`),
        `${name}: ${String(error)}`,
      );
    else {
      const failure = object(error);
      assert.equal(failure.kind, expected.kind, name);
      assert.equal(failure.stage, expected.stage, name);
    }
    results.push({ name, result: { status: 'rejected', expected } });
  }
  assert(caught, `${name} unexpectedly accepted`);
}
async function rawCall(
  index: number,
  entrypoint: string,
  calldata: readonly string[],
  address = deployment.registryAddress,
) {
  const selected = fixed[index];
  assert(selected);
  const sent = object(
    await selected.account.execute([
      { contractAddress: address, entrypoint, calldata: [...calldata] },
    ]),
  );
  await selected.account.wait(hex(sent.transaction_hash));
  const confirmed = await receipt(rpc, hex(sent.transaction_hash));
  assert.equal(confirmed.status, 'succeeded');
  return confirmed;
}
async function realConsumerCall() {
  return transport(rpc).call(
    {
      contractAddress: accountAddress(hex(consumer.contract_address)),
      entrypoint: 'act',
      calldata: [e],
    },
    await block(),
  );
}
async function consumerAct(index: number, candidate: string) {
  return rawCall(
    index,
    'act',
    [candidate],
    accountAddress(hex(consumer.contract_address)),
  );
}
async function preview(account = accountA) {
  const states: PreviewState[] = [];
  await loadAssociationPreview(reader, account, await block(), [e], (state) =>
    states.push(state),
  );
  assert.equal(states[0]?.status, 'loading');
  const ready = states[1];
  assert(ready?.status === 'ready');
  assert(ready.canAddWallet);
  return ready;
}
const initial = await preview();
assert(initial.promptRegistration);
assert.equal(initial.comparison.matches.length, 0);
await rejected(
  'configured-class-mismatch',
  async () =>
    createRegistryReader(
      { ...deployment, classHash: hex('0x123') },
      transport(rpc),
    ).getSigningDomain(await block()),
  { kind: 'deployment-mismatch', stage: 'query' },
);
await rejected(
  'configured-label-mismatch',
  async () =>
    createRegistryReader(
      { ...deployment, accountLabel: 'Wrong Label' },
      transport(rpc),
    ).getSigningDomain(await block()),
  { kind: 'deployment-mismatch', stage: 'query' },
);
const domain = await reader.getSigningDomain(await block());
assert.equal(domain.accountLabel, 'Local Registry');
assert.equal(domain.registryAddress, deployment.registryAddress);
assert.equal(domain.accountChainId, CHAIN_ID);
results.push({ name: 'authenticated-deployment', result: domain });
const link = await sign(a, 'link');
matched('initial-link', await a.submit([link]));
const linkedPreview = await preview();
assert(!linkedPreview.promptRegistration);
assert.deepEqual(linkedPreview.comparison.matches, [e]);
await rejected(
  'zero-immediate-caller',
  async () => realConsumerCall(),
  'CONSUMER_ZERO_CALLER',
);
await consumerAct(0, e);
results.push({ name: 'allowed-linked', result: 'accepted' });
await rejected(
  'allowed-unlinked',
  () => consumerAct(0, '0x123'),
  'CONSUMER_NOT_ASSOCIATED',
);
await rejected(
  'wrong-caller',
  () => consumerAct(1, e),
  'CONSUMER_NOT_ASSOCIATED',
);
await rejected(
  'zero-candidate',
  () => consumerAct(0, '0x0'),
  'CONSUMER_ZERO_CANDIDATE',
);
await rejected(
  'forwarded-caller',
  () =>
    rawCall(
      0,
      'forward',
      [String(consumer.contract_address), e],
      accountAddress(hex(forwarder.contract_address)),
    ),
  'CONSUMER_NOT_ASSOCIATED',
);
await rejected(
  'link-replay',
  () => rawCall(0, 'link', a.encode(link).calldata),
  'AR_STALE_ETH_NONCE',
);
matched(
  'multiwallet-batch',
  await a.submit([
    await sign(a, 'link', wallet2),
    await sign(a, 'link', wallet3),
  ]),
);
assert.equal(await reader.getEthereumAddressCount(accountA, await block()), 3n);
assert.deepEqual(
  new Set(
    (await reader.listAllEthereumAddresses(accountA, await block()))
      .ethereumAddresses,
  ),
  new Set([e, e2, e3]),
);
await rejected(
  'linked-disallowed',
  () => consumerAct(0, e2),
  'CONSUMER_NOT_ALLOWED',
);
matched('selective-unlink', await a.unlink(e2));
assert(await reader.isAssociated(e3, accountA, await block()));
matched('move', await b.submit([await sign(b, 'move')]));
assert.equal(linkedPreview.comparison.matches.length, 1); // stale preview remains a historical fact
await rejected(
  'stale-preview-after-move',
  () => consumerAct(0, e),
  'CONSUMER_NOT_ASSOCIATED',
);
await consumerAct(1, e);
matched(
  'linked-revoke-other-account',
  await c.submit([await sign(c, 'revoke')]),
);
await rejected(
  'stale-preview-after-revoke',
  () => consumerAct(1, e),
  'CONSUMER_NOT_ASSOCIATED',
);
matched(
  'unlinked-revoke-other-account',
  await c.submit([await sign(c, 'revoke')]),
);
const pending = await sign(a, 'link');
matched('current-pair-cancellation', await a.invalidatePendingIncoming(e));
await rejected(
  'stale-recipient-calldata',
  () => rawCall(0, 'link', a.encode(pending).calldata),
  'AR_STALE_RECIP_NONCE',
);
const fresh = await sign(a, 'link');
const validCall = a.encode(fresh);
assert(fresh.prepared.operation === 'link');
// Independently sign each altered message so its intended guard is isolated.
for (const [name, field, value, index, expected] of [
  [
    'future-ethereum-nonce',
    'ethereumNonce',
    fresh.prepared.request.ethereumNonce + 1n,
    2,
    'AR_STALE_ETH_NONCE',
  ],
  ['stale-ethereum-nonce', 'ethereumNonce', 0n, 2, 'AR_STALE_ETH_NONCE'],
  [
    'future-recipient-nonce',
    'recipientNonce',
    fresh.prepared.request.recipientNonce + 1n,
    4,
    'AR_STALE_RECIP_NONCE',
  ],
  ['zero-deadline', 'deadline', 0n, 6, 'AR_BAD_DEADLINE'],
  ['expired-deadline', 'deadline', 1n, 6, 'AR_EXPIRED'],
] as const) {
  const typed = {
    ...fresh.prepared.typedData,
    message: { ...fresh.prepared.typedData.message, [field]: value.toString() },
  };
  const signature = parseSignature(
    await wallet.sign({
      hash: hashTypedData(
        typed as unknown as Parameters<typeof hashTypedData>[0],
      ),
    }),
  );
  const calldata = [...validCall.calldata];
  calldata.splice(
    index,
    field === 'deadline' ? 1 : 2,
    ...(field === 'deadline' ? [value.toString()] : limbs(value)),
  );
  calldata.splice(
    7,
    5,
    ...limbs(signature.r),
    ...limbs(signature.s),
    Number(signature.yParity).toString(),
  );
  await rejected(name, () => rawCall(0, 'link', calldata), expected);
}
// Zero and out-of-range addresses cannot represent a matching Ethereum signer.
// Native malformed values must fail decoding, before application signature checks.
for (const [name, index, value, expected] of [
  ['zero-address', 0, '0', 'AR_ZERO_ADDRESS'],
  [
    'invalid-native-address',
    0,
    (1n << 160n).toString(),
    'Failed to deserialize param #1',
  ],
  ['invalid-parity', 11, '2', 'Failed to deserialize param #2'],
  ['zero-r', 7, '0', 'AR_BAD_SIGNATURE'],
] as const) {
  const calldata = [...validCall.calldata];
  calldata[index] = value;
  await rejected(name, () => rawCall(0, 'link', calldata), expected);
}
await rejected(
  'truncated-calldata',
  () => rawCall(0, 'link', validCall.calldata.slice(0, -1)),
  'Failed to deserialize param #2',
);
await rejected(
  'wrong-link-caller',
  () => rawCall(1, 'link', validCall.calldata),
  'AR_BAD_CALLER',
);
assert.equal(
  await reader.getStarknetAddress(e, await block()),
  accountAddress(hex('0x0')),
);
// Sign altered consent/domain data directly only as adversarial calldata fixtures.
for (const [name, typed] of [
  [
    'wrong-statement',
    {
      ...fresh.prepared.typedData,
      message: {
        ...fresh.prepared.typedData.message,
        statement: 'Different consent',
      },
    },
  ],
  [
    'wrong-domain-version',
    {
      ...fresh.prepared.typedData,
      domain: { ...fresh.prepared.typedData.domain, version: '2' },
    },
  ],
  [
    'wrong-ethereum-chain',
    {
      ...fresh.prepared.typedData,
      domain: { ...fresh.prepared.typedData.domain, chainId: '1' },
    },
  ],
  [
    'wrong-domain-salt',
    {
      ...fresh.prepared.typedData,
      domain: {
        ...fresh.prepared.typedData.domain,
        salt: `0x${'01'.repeat(32)}` as const,
      },
    },
  ],
] as const) {
  // Deliberately invalid protocol fields use independent Ethereum hashing.
  const bad = parseSignature(
    await wallet.sign({
      hash: hashTypedData(
        typed as unknown as Parameters<typeof hashTypedData>[0],
      ),
    }),
  );
  const calldata = [...validCall.calldata];
  calldata.splice(
    7,
    5,
    ...limbs(bad.r),
    ...limbs(bad.s),
    Number(bad.yParity).toString(),
  );
  await rejected(name, () => rawCall(0, 'link', calldata), 'AR_BAD_SIGNATURE');
}
for (const [name, r, s, parity] of [
  [
    'high-s',
    fresh.signature.r,
    0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141n -
      fresh.signature.s,
    !fresh.signature.yParity,
  ],
  ['zero-r-both-limbs', 0n, fresh.signature.s, fresh.signature.yParity],
  [
    'wrong-parity',
    fresh.signature.r,
    fresh.signature.s,
    !fresh.signature.yParity,
  ],
] as const) {
  const calldata = [...validCall.calldata];
  calldata.splice(7, 5, ...limbs(r), ...limbs(s), Number(parity).toString());
  await rejected(name, () => rawCall(0, 'link', calldata), 'AR_BAD_SIGNATURE');
}
matched('fresh-after-cancel', await a.submit([fresh]));
// SDK success classification survives a later transport read failure at the real receipt block.
let failRead = false;
const realTransport = transport(rpc);
const failingReader = createRegistryReader(deployment, {
  ...realTransport,
  async call(call, hash) {
    if (failRead) throw new Error('injected post-confirmation read outage');
    return realTransport.call(call, hash);
  },
});
const outageClient = createRegistryClient({
  deployment,
  reader: failingReader,
  account: {
    ...first.adapter,
    async wait(hash) {
      const value = await first.adapter.wait(hash);
      failRead = true;
      return value;
    },
  },
});
const outage = await outageClient.unlink(e);
assert.equal(outage.receipt.status, 'succeeded');
assert.equal(outage.readback.status, 'unavailable');
assert.equal(outage.receipt.blockHash, outage.readback.blockHash);
results.push({ name: 'receipt-read-outage', result: outage });
assert.equal(
  await reader.getStarknetAddress(e, await block()),
  accountAddress(hex('0x0')),
);
// A valid successful receipt is retained even when a faulty later read contradicts it.
let mismatchRead = false;
const mismatchingReader = createRegistryReader(deployment, {
  ...realTransport,
  async call(call, hash) {
    if (mismatchRead && call.entrypoint === 'get_starknet_address')
      return ['0x0'];
    return realTransport.call(call, hash);
  },
});
const mismatchClient = createRegistryClient({
  deployment,
  reader: mismatchingReader,
  account: {
    ...first.adapter,
    async wait(hash) {
      const value = await first.adapter.wait(hash);
      mismatchRead = true;
      return value;
    },
  },
});
const mismatch = await mismatchClient.submit([
  await sign(mismatchClient, 'link'),
]);
assert.equal(mismatch.receipt.status, 'succeeded');
assert.equal(mismatch.readback.status, 'mismatch');
assert.equal(mismatch.receipt.blockHash, mismatch.readback.blockHash);
assert(await reader.isAssociated(e, accountA, mismatch.receipt.blockHash));
results.push({ name: 'receipt-read-mismatch', result: mismatch });
// Deliberate future nonce fixture bypasses the official client's current-nonce signer.
const base = await a.prepareLink(ethereumAddress(wallet4.address));
assert(base.operation === 'link');
const futureTyped = {
  ...base.typedData,
  message: {
    ...base.typedData.message,
    ethereumNonce: (base.request.ethereumNonce + 1n).toString(),
  },
};
const signature = parseSignature(
  await wallet4.sign({ hash: typedDigest(futureTyped) }),
);
const request = {
  ...base.request,
  ethereumNonce: base.request.ethereumNonce + 1n,
};

const futureCalldata = [
  request.ethereumAddress,
  request.accountAddress,
  ...limbs(request.ethereumNonce),
  ...limbs(request.recipientNonce),
  request.deadline.toString(),
  ...limbs(signature.r),
  ...limbs(signature.s),
  Number(signature.yParity).toString(),
];
await rejected(
  'deliberately-future-signature-initially-rejected',
  () => rawCall(0, 'link', futureCalldata),
  'AR_STALE_ETH_NONCE',
);
matched(
  'advance-future-ethereum-nonce',
  await c.submit([await sign(c, 'revoke', wallet4)]),
);
await rawCall(0, 'link', futureCalldata);
assert(
  await reader.isAssociated(
    ethereumAddress(wallet4.address),
    accountA,
    await block(),
  ),
);
results.push({
  name: 'future-signature-becomes-current',
  result: 'accepted; cancellation does not invalidate every future signature',
});
const failedStates: PreviewState[] = [];
await loadAssociationPreview(
  failingReader,
  accountA,
  await block(),
  [e],
  (state) => failedStates.push(state),
);
assert.equal(failedStates[0]?.status, 'loading');
assert.equal(failedStates[1]?.status, 'error');
const output = join(dirname(manifestPath), 'lifecycle-results.json');
assert(
  results.length >= 45,
  'Integration must execute a nonempty complete case set',
);
writeFileSync(
  output,
  JSON.stringify(
    { softwareSignerOnly: true, checks: results },
    (_, value: unknown) =>
      typeof value === 'bigint' ? value.toString() : value,
    2,
  ),
);
console.log(
  `PASS ${String(results.length)} real local integration checks; ${output}`,
);
