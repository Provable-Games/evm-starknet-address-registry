import { expect, test } from 'vitest';
import {
  consumerLock,
  type PackageLock,
} from '../../../scripts/sdk-consumer-lock.ts';

function locked(version: string, dependencies = {}) {
  return {
    version,
    resolved: `https://registry.npmjs.org/mock/-/mock-${version}.tgz`,
    integrity: `sha512-synthetic-${version}`,
    dependencies,
  };
}
function fixture(): PackageLock {
  return {
    lockfileVersion: 3,
    packages: {
      '': { devDependencies: { typescript: '6.0.3' } },
      'packages/sdk': {
        name: '@test/sdk',
        version: '0.0.0',
        dependencies: { alpha: '1.0.0' },
      },
      'node_modules/alpha': {
        ...locked('1.0.0', { '@scope/nested': '1.0.0' }),
        peerDependencies: { peer: '1.0.0', typescript: '>=5', absent: '*' },
        peerDependenciesMeta: {
          typescript: { optional: true },
          absent: { optional: true },
        },
      },
      'node_modules/alpha/node_modules/@scope/nested': locked('1.0.0', {
        peer: '1.0.0',
      }),
      'node_modules/@scope/nested': locked('2.0.0'),
      'node_modules/peer': locked('1.0.0'),
      'node_modules/typescript': { ...locked('6.0.3'), devOptional: true },
      'node_modules/dev-only': { ...locked('1.0.0'), dev: true },
    },
  };
}
function project(source = fixture()) {
  return consumerLock(source, '@test/sdk', 'file:sdk.tgz', 'sha512-packed');
}
test('consumer closure preserves nested scoped resolution and required peers without compiler/dev graph', () => {
  const source = fixture(),
    result = project(source);
  expect(Object.keys(result.packages).sort()).toEqual([
    '',
    'node_modules/@test/sdk',
    'node_modules/alpha',
    'node_modules/alpha/node_modules/@scope/nested',
    'node_modules/peer',
  ]);
  expect(
    result.packages['node_modules/alpha/node_modules/@scope/nested'],
  ).toEqual(source.packages['node_modules/alpha/node_modules/@scope/nested']);
  expect(result.packages['node_modules/@test/sdk']).toMatchObject({
    resolved: 'file:sdk.tgz',
    integrity: 'sha512-packed',
  });
});
test('workspace-local dependency paths relocate under the packed package and preserve cycles', () => {
  const source = fixture();
  source.packages['packages/sdk/node_modules/alpha'] = locked('1.0.0', {
    beta: '1.0.0',
  });
  source.packages['packages/sdk/node_modules/beta'] = locked('1.0.0', {
    alpha: '1.0.0',
  });
  const result = project(source);
  expect(Object.keys(result.packages).sort()).toEqual([
    '',
    'node_modules/@test/sdk',
    'node_modules/@test/sdk/node_modules/alpha',
    'node_modules/@test/sdk/node_modules/beta',
  ]);
});
test('missing required peers and non-registry runtime links fail closed', () => {
  const missing = fixture();
  delete missing.packages['node_modules/peer'];
  expect(() => project(missing)).toThrow('Missing locked runtime dependency');
  const linked = fixture();
  linked.packages['node_modules/peer'] = { link: true, resolved: '../outside' };
  expect(() => project(linked)).toThrow('reviewed registry resolution');
});
