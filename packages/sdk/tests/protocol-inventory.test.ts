import { expect, test } from 'vitest';
import { readFileSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  checkClassAbiEntries,
  checkSdkProtocolIdentity,
} from '../../../scripts/sdk-protocol-identity.ts';
import {
  sourceFunctions,
  checkFunctionInventory,
} from '../../../scripts/sdk-function-inventory.ts';
import { ABI_SHA256, PROTOCOL_REVISION } from '../src/index.js';

test('SDK exported identities are tied to actual frozen ABI bytes and provenance', () => {
  const abi = readFileSync(
    new URL('../../../protocol/abi.json', import.meta.url),
  );
  const provenance = JSON.parse(
    readFileSync(
      new URL('../../../protocol/abi.provenance.json', import.meta.url),
      'utf8',
    ),
  ) as { abi_sha256: string; approved_signing_revision: string };
  const sdk = { ABI_SHA256, PROTOCOL_REVISION };
  expect(() => {
    checkSdkProtocolIdentity(abi, provenance, sdk);
  }).not.toThrow();
  expect(() => {
    checkSdkProtocolIdentity(
      Buffer.concat([abi, Buffer.from(' ')]),
      provenance,
      sdk,
    );
  }).toThrow('Frozen ABI bytes differ');
  expect(() => {
    checkSdkProtocolIdentity(abi, { ...provenance, abi_sha256: 'stale' }, sdk);
  }).toThrow();
  expect(() => {
    checkSdkProtocolIdentity(abi, provenance, { ...sdk, ABI_SHA256: 'stale' });
  }).toThrow('SDK ABI identity drift');
  expect(() => {
    checkSdkProtocolIdentity(
      abi,
      { ...provenance, approved_signing_revision: 'stale' },
      sdk,
    );
  }).toThrow('SDK signing revision drift');
  expect(() => {
    checkSdkProtocolIdentity(abi, provenance, {
      ...sdk,
      PROTOCOL_REVISION: 'stale',
    });
  }).toThrow('SDK signing revision drift');
});
test('release identity preserves native L1 entry contents and multiplicity across compiler ordering', () => {
  const frozen = { type: 'interface', name: 'Registry' };
  const first = { name: 'get_l1_link_proposal' };
  const second = { name: 'accept_l1_link' };
  const extension = { type: 'interface', items: [first, second] };
  const compiled = [extension, frozen];
  checkClassAbiEntries(compiled, [frozen], [extension]);
  for (const altered of [
    [{ ...extension, items: [second, first] }],
    [extension, extension],
    [],
  ]) {
    expect(() => {
      checkClassAbiEntries(compiled, [frozen], altered);
    }).toThrow('Compiled ABI differs');
  }
});

test('inventory checks detect source-position drift without writing and explicit regeneration is repeatable', () => {
  const temporary = mkdtempSync(join(tmpdir(), 'sdk-inventory-'));
  try {
    const path = join(temporary, 'inventory.json');
    const source = 'export function sample() { return 1; }\n';
    const initial = { 'sample.ts': sourceFunctions('sample.ts', source) };
    writeFileSync(path, JSON.stringify(initial, null, 2) + '\n');
    const before = readFileSync(path, 'utf8');
    checkFunctionInventory(path, initial, false);
    const shifted = {
      'sample.ts': sourceFunctions('sample.ts', '\n' + source),
    };
    expect(() => {
      checkFunctionInventory(path, shifted, false);
    }).toThrow('Function inventory drift');
    expect(readFileSync(path, 'utf8')).toBe(before);
    checkFunctionInventory(path, shifted, true);
    const updated = readFileSync(path, 'utf8');
    expect(updated).not.toBe(before);
    checkFunctionInventory(path, shifted, false);
    checkFunctionInventory(path, shifted, true);
    expect(readFileSync(path, 'utf8')).toBe(updated);
    const extra = {
      ...shifted,
      'extra.ts': sourceFunctions('extra.ts', 'export const extra = () => 2;'),
    };
    expect(() => {
      checkFunctionInventory(path, extra, false);
    }).toThrow('Function inventory drift');
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});
