import assert from 'node:assert/strict';

interface LockEntry {
  version?: string;
  resolved?: string;
  integrity?: string;
  link?: boolean;
  dev?: boolean;
  devOptional?: boolean;
  dependencies?: Record<string, string>;
  optionalDependencies?: Record<string, string>;
  peerDependencies?: Record<string, string>;
  peerDependenciesMeta?: Record<string, { optional?: boolean }>;
  [key: string]: unknown;
}
export interface PackageLock {
  lockfileVersion: number;
  packages: Record<string, LockEntry>;
}

/** Relocate only the SDK runtime closure from the reviewed workspace lock. */
export function consumerLock(
  source: PackageLock,
  sdkName: string,
  archive: string,
  integrity: string,
): PackageLock {
  assert.equal(source.lockfileVersion, 3);
  const workspace = 'packages/sdk';
  const destination = `node_modules/${sdkName}`;
  const sdk = source.packages[workspace];
  assert.ok(sdk?.version && sdk.dependencies);
  assert.equal(sdk.name, sdkName);
  const packages: Record<string, LockEntry> = {
    '': { dependencies: { [sdkName]: archive } },
    [destination]: { ...sdk, resolved: archive, integrity },
  };
  const visited = new Set<string>();
  function locate(from: string, name: string): string | undefined {
    let parent = from;
    for (;;) {
      const key = `${parent ? parent + '/' : ''}node_modules/${name}`;
      if (source.packages[key]) return key;
      if (!parent) return undefined;
      const index = parent.lastIndexOf('/node_modules/');
      parent = index < 0 ? '' : parent.slice(0, index);
    }
  }
  function visit(from: string): void {
    if (visited.has(from)) return;
    visited.add(from);
    const entry = source.packages[from];
    assert.ok(entry);
    const edges = new Map<string, { optional: boolean; peer: boolean }>();
    for (const name of Object.keys(entry.dependencies ?? {}))
      edges.set(name, { optional: false, peer: false });
    for (const name of Object.keys(entry.optionalDependencies ?? {}))
      edges.set(name, { optional: true, peer: false });
    for (const name of Object.keys(entry.peerDependencies ?? {}))
      if (!edges.has(name))
        edges.set(name, {
          optional: entry.peerDependenciesMeta?.[name]?.optional === true,
          peer: true,
        });
    for (const [name, edge] of edges) {
      const key = locate(from, name);
      const dependency = key === undefined ? undefined : source.packages[key];
      if (
        edge.optional &&
        (!dependency ||
          (edge.peer && (dependency.dev || dependency.devOptional)))
      )
        continue;
      assert.ok(
        key && dependency,
        `Missing locked runtime dependency ${from}: ${name}`,
      );
      assert.ok(
        !dependency.link &&
          dependency.version &&
          dependency.integrity &&
          dependency.resolved?.startsWith('https://registry.npmjs.org/'),
        `Runtime dependency must have a reviewed registry resolution: ${key}`,
      );
      const relocated = key.startsWith(workspace + '/')
        ? destination + key.slice(workspace.length)
        : key;
      assert.ok(relocated.startsWith('node_modules/'));
      const copy = { ...dependency };
      delete copy.dev;
      delete copy.devOptional;
      packages[relocated] = copy;
      visit(key);
    }
  }
  visit(workspace);
  return { lockfileVersion: 3, packages };
}
