import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { runInNewContext } from 'node:vm';
import { gzipSync } from 'node:zlib';
import { build } from 'rolldown';
import { consumerLock, type PackageLock } from './sdk-consumer-lock.ts';
import { checkSdkProtocolIdentity } from './sdk-protocol-identity.ts';
import { retainCheckedPackage } from './sdk-package-retention.ts';

const root = fileURLToPath(new URL('../', import.meta.url));
const args = process.argv.slice(2);
assert.ok(
  args.length === 0 ||
    (args.length === 2 && args[0] === '--output' && args[1]?.length),
  'Usage: node scripts/check-sdk-package.ts [--output <new-directory>]',
);
const outputDirectory = args[1] === undefined ? undefined : resolve(args[1]);
function sourceIdentity() {
  const files = [
    'package.json',
    'package-lock.json',
    'toolchain.json',
    'tsconfig.base.json',
    'packages/sdk/package.json',
    'packages/sdk/tsconfig.build.json',
    'packages/sdk/LICENSE',
    'packages/sdk/README.md',
    'packages/sdk/CHANGELOG.md',
    'scripts/check-sdk-package.ts',
    'scripts/sdk-package-retention.ts',
    'scripts/sdk-consumer-lock.ts',
    'scripts/sdk-protocol-identity.ts',
    'protocol/abi.json',
    'protocol/abi.provenance.json',
    'protocol/vectors.json',
    ...readdirSync(join(root, 'packages/sdk/src'))
      .filter((file) => file.endsWith('.ts'))
      .map((file) => `packages/sdk/src/${file}`),
  ].sort();
  return {
    revision: execFileSync('git', ['rev-parse', 'HEAD'], {
      cwd: root,
      encoding: 'utf8',
    }).trim(),
    dirty:
      execFileSync('git', ['status', '--porcelain'], {
        cwd: root,
        encoding: 'utf8',
      }).trim().length > 0,
    sha256: Object.fromEntries(
      files.map((file) => [
        file,
        createHash('sha256')
          .update(readFileSync(join(root, file)))
          .digest('hex'),
      ]),
    ),
  };
}
const source = sourceIdentity();
let retained:
  | { filename: string; archive: Buffer; evidence: Record<string, unknown> }
  | undefined;
const consumer = mkdtempSync(join(tmpdir(), 'registry-sdk-consumer-'));

function run(command: string, args: string[], cwd = consumer): void {
  execFileSync(command, args, { cwd, stdio: 'inherit' });
}

try {
  mkdirSync(resolve(root, 'packages/sdk/dist'), { recursive: true });
  writeFileSync(
    resolve(root, 'packages/sdk/dist/stale.js'),
    'export const stale = true;',
  );
  run(
    'npm',
    [
      'pack',
      '--workspace',
      '@provable-games/evm-starknet-address-registry',
      '--pack-destination',
      consumer,
    ],
    root,
  );
  const archives = readdirSync(consumer).filter((file) =>
    file.endsWith('.tgz'),
  );
  assert.equal(archives.length, 1, 'Expected exactly one packed SDK archive');
  const archive = archives[0];
  assert.ok(archive);
  const archiveBytes = readFileSync(join(consumer, archive));
  const sdkName = '@provable-games/evm-starknet-address-registry';
  const sourceLock = JSON.parse(
    readFileSync(join(root, 'package-lock.json'), 'utf8'),
  ) as PackageLock;
  const sdkManifest = JSON.parse(
    readFileSync(join(root, 'packages/sdk/package.json'), 'utf8'),
  ) as { name: string; version: string; dependencies: Record<string, string> };
  assert.equal(sdkManifest.name, sdkName);
  assert.equal(
    sdkManifest.version,
    sourceLock.packages['packages/sdk']?.version,
  );
  assert.deepEqual(
    sdkManifest.dependencies,
    sourceLock.packages['packages/sdk']?.dependencies,
  );
  const projected = consumerLock(
    sourceLock,
    sdkName,
    `file:${archive}`,
    'sha512-' + createHash('sha512').update(archiveBytes).digest('base64'),
  );
  writeFileSync(
    join(consumer, 'package.json'),
    JSON.stringify({
      private: true,
      type: 'module',
      dependencies: projected.packages['']?.dependencies,
    }),
  );
  const lockText = JSON.stringify(projected);
  writeFileSync(join(consumer, 'package-lock.json'), lockText);
  // Use the caller's effective cache; CI exports the same cache for root and consumer.
  const cache = execFileSync('npm', ['config', 'get', 'cache'], {
    cwd: root,
    encoding: 'utf8',
  }).trim();
  run('npm', [
    'ci',
    '--offline',
    '--ignore-scripts',
    '--no-audit',
    '--no-fund',
    '--cache',
    cache,
  ]);
  assert.equal(
    readFileSync(join(consumer, 'package-lock.json'), 'utf8'),
    lockText,
  );
  run('npm', ['ls', '--all', '--omit=dev']);
  const installedLock = JSON.parse(
    readFileSync(join(consumer, 'node_modules/.package-lock.json'), 'utf8'),
  ) as PackageLock;
  assert.deepEqual(
    Object.keys(installedLock.packages).sort(),
    Object.keys(projected.packages)
      .filter((key) => key !== '')
      .sort(),
    'Installed runtime closure differs from the reviewed projection',
  );
  for (const [key, entry] of Object.entries(installedLock.packages)) {
    const expected = projected.packages[key];
    assert.ok(expected);
    assert.equal(entry.version, expected.version);
    assert.equal(entry.integrity, expected.integrity);
    assert.equal(entry.resolved, expected.resolved);
  }
  assert.ok(
    !readdirSync(
      join(
        consumer,
        'node_modules/@provable-games/evm-starknet-address-registry/dist',
      ),
    ).includes('stale.js'),
    'Prepack must remove stale generated files',
  );
  writeFileSync(
    join(consumer, 'consumer.mjs'),
    `
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import * as sdk from '@provable-games/evm-starknet-address-registry';
assert.equal(typeof sdk.createRegistryClient, 'function');
assert.equal(typeof sdk.createRegistryReader, 'function');
assert.equal(typeof sdk.compareLinkedAddresses, 'function');
assert.equal(sdk.SDK_STATUS, 'implemented');
`,
  );
  checkSdkProtocolIdentity(
    readFileSync(join(root, 'protocol/abi.json')),
    JSON.parse(
      readFileSync(join(root, 'protocol/abi.provenance.json'), 'utf8'),
    ) as {
      abi_sha256: string;
      approved_signing_revision: string;
    },
    (await import(
      pathToFileURL(join(consumer, 'node_modules', sdkName, 'dist/index.js'))
        .href
    )) as {
      ABI_SHA256: string;
      PROTOCOL_REVISION: string;
    },
  );
  assert.equal(
    readFileSync(
      join(consumer, `node_modules/${sdkName}/CHANGELOG.md`),
      'utf8',
    ),
    readFileSync(join(root, 'packages/sdk/CHANGELOG.md'), 'utf8'),
    'Packed changelog must match the README link',
  );
  const installedManifest = JSON.parse(
    readFileSync(
      join(consumer, `node_modules/${sdkName}/package.json`),
      'utf8',
    ),
  ) as typeof sdkManifest;
  assert.deepEqual(installedManifest.dependencies, sdkManifest.dependencies);
  run(process.execPath, ['consumer.mjs']);
  writeFileSync(
    join(consumer, 'consumer.ts'),
    `
import { SDK_STATUS } from '@provable-games/evm-starknet-address-registry';
import type { LinkRequest, MoveRequest, RevokeRequest, Signature, RegistryClient, RegistryClientError, TypedData, Hash32, RegistryReader, TrustedDeployment, SubmissionResult, CompareLinkedAddresses, LinkedAddressSnapshot } from '@provable-games/evm-starknet-address-registry';
const status: 'implemented' = SDK_STATUS;
const link: LinkRequest = { ethereumAddress: '0x0000000000000000000000000000000000000001', accountAddress: '0x0000000000000000000000000000000000000000000000000000000000000002', ethereumNonce: 1n << 200n, recipientNonce: 0n, deadline: (1n << 64n) - 1n };
const move: MoveRequest = { ...link, previousAccountAddress: '0x0000000000000000000000000000000000000000000000000000000000000003' };
const revoke: RevokeRequest = { ethereumAddress: link.ethereumAddress, currentAccountAddress: '0x0000000000000000000000000000000000000000000000000000000000000000', ethereumNonce: link.ethereumNonce, deadline: link.deadline };
const signature: Signature = { r: 1n, s: 2n, yParity: false };
// @ts-expect-error Protocol integers must not silently accept JavaScript numbers.
const invalid: LinkRequest = { ...link, ethereumNonce: 9007199254740992 };
declare const linkTypedData: Extract<TypedData, { readonly primaryType: 'LinkAddress' }>;
const { recipientNonce: omittedRecipientNonce, ...missingRecipient } = linkTypedData.message;
// @ts-expect-error LinkAddress requires recipientNonce.
const missingField: TypedData = { ...linkTypedData, message: missingRecipient };
// @ts-expect-error LinkAddress must not contain a move-only previous account.
const wrongField: TypedData = { ...linkTypedData, message: { ...linkTypedData.message, previousAccountAddress: '0x0000000000000000000000000000000000000000000000000000000000000003' } };
// @ts-expect-error EIP712Domain and the exact primary type definition are both required.
const missingType: TypedData = { ...linkTypedData, types: { EIP712Domain: linkTypedData.types.EIP712Domain } };
// @ts-expect-error Field names and Solidity types must retain the approved tuple order.
const wrongTypeField: typeof linkTypedData.types.LinkAddress[0] = { name: 'statement', type: 'bytes32' };
void [omittedRecipientNonce, missingField, wrongField, missingType, wrongTypeField];
declare const client: RegistryClient;
declare const trusted: TrustedDeployment;
const revision: '5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a' = trusted.protocolRevision;
declare const result: SubmissionResult;
const confirmed: 'succeeded' = result.receipt.status;
const transactionHash: string = result.receipt.transactionHash;
if (result.readback.status === 'unavailable') {
  const originalCause: unknown = result.readback.cause;
  void originalCause;
} else {
  const observedNonce: bigint | undefined = result.readback.observations[0]?.ethereumNonce;
  void observedNonce;
}
declare const failure: RegistryClientError;
if (failure.kind === 'confirmation-unavailable') {
  const submittedHash: Hash32 = failure.transactionHash;
  const waitStage: 'wait' = failure.stage;
  const originalCause: unknown = failure.cause;
  void [submittedHash, waitStage, originalCause];
}
// @ts-expect-error Unknown confirmation after submission must retain the transaction hash.
const missingHash: RegistryClientError = Object.assign(new Error('fixture'), { kind: 'confirmation-unavailable' as const, stage: 'wait' as const, cause: 'timeout' });
// @ts-expect-error Confirmation-unavailable is specifically an inconclusive wait.
const wrongStage: RegistryClientError = Object.assign(new Error('fixture'), { kind: 'confirmation-unavailable' as const, stage: 'execute' as const, transactionHash: '0x0000000000000000000000000000000000000000000000000000000000000001' as const, cause: 'timeout' });
const disconnected: RegistryClientError = Object.assign(new Error('fixture'), { kind: 'disconnected' as const, stage: 'prepare' as const, cause: 'disconnect' });
const standardError: Error = disconnected;
// @ts-expect-error SDK errors must retain the standard Error shape.
const plainObjectError: RegistryClientError = { kind: 'disconnected', stage: 'prepare', message: 'fixture' };
// @ts-expect-error Registry builders only emit the five frozen mutation names.
const mistypedCall: ReturnType<RegistryClient['buildUnlinkCall']> = { contractAddress: '0x0000000000000000000000000000000000000000000000000000000000000000', calldata: [], entrypoint: 'unlnik' };
void [standardError, plainObjectError, mistypedCall];
void [missingHash, wrongStage, disconnected];
declare const compareLinkedAddresses: CompareLinkedAddresses;
declare const snapshot: LinkedAddressSnapshot;
declare const reader: RegistryReader;
const listed: Promise<LinkedAddressSnapshot> = reader.listAllEthereumAddresses('0x0000000000000000000000000000000000000000000000000000000000000002', '0x0000000000000000000000000000000000000000000000000000000000000123');
const comparison = compareLinkedAddresses(snapshot, ['0x0000000000000000000000000000000000000001']);
const unlinkCall = client.buildUnlinkCall('0x0000000000000000000000000000000000000001');
const cancelCall = client.buildInvalidatePendingIncomingCall('0x0000000000000000000000000000000000000001');
void [status, link, move, revoke, signature, invalid, client, revision, confirmed, transactionHash, comparison, listed, unlinkCall, cancelCall];
`,
  );
  writeFileSync(
    join(consumer, 'tsconfig.json'),
    JSON.stringify({
      compilerOptions: {
        strict: true,
        noUncheckedIndexedAccess: true,
        exactOptionalPropertyTypes: true,
        module: 'NodeNext',
        moduleResolution: 'NodeNext',
        target: 'ES2022',
        lib: ['ES2022'],
        types: [],
        noEmit: true,
      },
      files: ['consumer.ts'],
    }),
  );
  run(process.execPath, [
    resolve(root, 'node_modules/typescript/bin/tsc'),
    '-p',
    'tsconfig.json',
  ]);
  const compatibilityCompiler = process.env.SDK_CONSUMER_TSC;
  if (compatibilityCompiler) {
    const version = execFileSync(
      process.execPath,
      [compatibilityCompiler, '--version'],
      { encoding: 'utf8' },
    ).trim();
    assert.equal(
      version,
      'Version 5.8.3',
      'Compatibility mode requires exact TypeScript5.8.3',
    );
    run(process.execPath, [compatibilityCompiler, '-p', 'tsconfig.json']);
  }
  process.stdout.write(
    'Packed SDK ESM import and strict declaration consumer passed.\n',
  );
  const fixtures = (
    JSON.parse(
      readFileSync(resolve(root, 'protocol/vectors.json'), 'utf8'),
    ) as {
      vectors: {
        typed_data: unknown;
        signature: { v_0_1: string };
        hashes: { digest: string };
      }[];
    }
  ).vectors;
  writeFileSync(
    join(consumer, 'browser.mjs'),
    `
import * as sdk from '@provable-games/evm-starknet-address-registry';
if (typeof process !== 'undefined' || typeof Buffer !== 'undefined' || typeof require !== 'undefined') throw new Error('Node globals leaked');
globalThis.__sdkResult = (async () => {
  const results = [];
  for (const fixture of globalThis.__fixtures) {
    const digest = sdk.typedDigest(fixture.typed_data);
    const recovered = await sdk.recoverSigner(digest, sdk.parseSignature(fixture.signature.v_0_1), fixture.typed_data.message.ethereumAddress);
    results.push({digest, recovered});
  }
  return { exports: Object.keys(sdk).sort(), results };
})();
`,
  );
  const bundle = await build({
    input: join(consumer, 'browser.mjs'),
    platform: 'browser',
    output: { format: 'iife', minify: true, codeSplitting: false },
  });
  const output = bundle.output;
  assert.equal(output.length, 1, 'Expected one complete browser module');
  const chunk = output[0];
  assert.equal(chunk.imports.length, 0, 'Browser build has external imports');
  const execution: unknown = runInNewContext(
    chunk.code + '\n__sdkResult',
    { TextEncoder, TextDecoder, __fixtures: fixtures },
    { timeout: 5000 },
  );
  assert.ok(
    execution &&
      typeof execution === 'object' &&
      'then' in execution &&
      typeof execution.then === 'function',
  );
  const result = await (execution as Promise<{
    exports: string[];
    results: { digest: string; recovered: string }[];
  }>);
  assert.equal(result.results.length, 13);
  for (const [index, row] of result.results.entries())
    assert.equal(row.digest, fixtures[index]?.hashes.digest);
  assert.ok(result.exports.includes('createRegistryClient'));
  const graph = Object.keys(chunk.modules)
    .map((file) => file.replace(consumer, '<packed-consumer>'))
    .sort();
  assert.deepEqual(
    readFileSync(join(consumer, archive)),
    archiveBytes,
    'Checked archive changed during validation',
  );
  assert.deepEqual(
    sourceIdentity(),
    source,
    'Package source changed during validation',
  );
  const report = {
    package: { name: sdkManifest.name, version: sdkManifest.version },
    source,
    node: process.version,
    npm: execFileSync('npm', ['--version'], {
      cwd: root,
      encoding: 'utf8',
    }).trim(),
    evidence:
      'Packed browser-target IIFE executed in isolated JS context; no actual wallet/browser claim',
    bytes: Buffer.byteLength(chunk.code),
    gzip_bytes: gzipSync(chunk.code).length,
    modules: graph,
    runtime_packages: Object.fromEntries(
      Object.entries(installedLock.packages).map(([key, entry]) => [
        key,
        {
          version: entry.version,
          resolved: entry.resolved,
          integrity: entry.integrity,
        },
      ]),
    ),
    archive_sha256: createHash('sha256').update(archiveBytes).digest('hex'),
    declarations_sha256: Object.fromEntries(
      readdirSync(
        join(
          consumer,
          'node_modules/@provable-games/evm-starknet-address-registry/dist',
        ),
      )
        .filter((file) => file.endsWith('.d.ts'))
        .sort()
        .map((file) => [
          file,
          createHash('sha256')
            .update(
              readFileSync(
                join(
                  consumer,
                  'node_modules/@provable-games/evm-starknet-address-registry/dist',
                  file,
                ),
              ),
            )
            .digest('hex'),
        ]),
    ),
    compatibility: compatibilityCompiler
      ? 'TypeScript5.8.3 ES2022-only declarations passed; no older-runtime claim'
      : 'Primary compiler only',
    vectors: result.results.length,
  };
  mkdirSync(resolve(root, 'coverage'), { recursive: true });
  writeFileSync(
    resolve(root, 'coverage/browser-bundle.json'),
    JSON.stringify(report, null, 2) + '\n',
  );
  if (outputDirectory !== undefined)
    retained = { filename: archive, archive: archiveBytes, evidence: report };
  process.stdout.write(
    `Packed browser target: ${String(report.bytes)} bytes, ${String(report.gzip_bytes)} gzip bytes; all13 digest/recovery fixtures passed without Node globals.\n`,
  );
} finally {
  rmSync(consumer, { recursive: true, force: true });
}

if (outputDirectory !== undefined) {
  assert.ok(retained, 'Missing checked package');
  retainCheckedPackage(
    outputDirectory,
    retained.filename,
    retained.archive,
    retained.evidence,
  );
  process.stdout.write(`Retained checked SDK package in ${outputDirectory}\n`);
}
