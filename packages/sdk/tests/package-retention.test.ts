import { createHash } from 'node:crypto';
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  symlinkSync,
  writeFileSync,
  lstatSync,
  existsSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { expect, test } from 'vitest';
import { retainCheckedPackage } from '../../../scripts/sdk-package-retention.ts';

const archive = Buffer.from('exact tested archive bytes');
const evidence = {
  archive_sha256: createHash('sha256').update(archive).digest('hex'),
  package: { name: 'fixture', version: '0.0.0' },
};

test('retention writes exactly the checked bytes and public evidence, with exclusive output', () => {
  const root = mkdtempSync(join(tmpdir(), 'sdk-retention-test-'));
  try {
    const output = join(root, 'checked');
    retainCheckedPackage(output, 'sdk.tgz', archive, evidence);
    expect(readdirSync(output).sort()).toEqual([
      'checked-package.json',
      'sdk.tgz',
    ]);
    expect(readFileSync(join(output, 'sdk.tgz'))).toEqual(archive);
    expect(
      JSON.parse(readFileSync(join(output, 'checked-package.json'), 'utf8')),
    ).toEqual({
      schema_version: 1,
      kind: 'local-checked-sdk-pack',
      archive: {
        filename: 'sdk.tgz',
        bytes: archive.length,
        sha256: evidence.archive_sha256,
      },
      evidence,
    });
    expect(() => {
      retainCheckedPackage(output, 'sdk.tgz', archive, evidence);
    }).toThrow();
    expect(readFileSync(join(output, 'sdk.tgz'))).toEqual(archive);
    for (const kind of ['file', 'directory', 'symlink', 'dangling-symlink']) {
      const destination = join(root, kind);
      if (kind === 'file') writeFileSync(destination, 'preserve');
      else if (kind === 'directory') mkdirSync(destination);
      else
        symlinkSync(
          kind === 'symlink' ? output : join(root, 'absent'),
          destination,
        );
      const before = lstatSync(destination);
      expect(() => {
        retainCheckedPackage(destination, 'sdk.tgz', archive, evidence);
      }).toThrow();
      expect(lstatSync(destination).ino).toBe(before.ino);
    }
    expect(readFileSync(join(root, 'file'), 'utf8')).toBe('preserve');
    expect(readdirSync(join(root, 'directory'))).toEqual([]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('mismatched bytes, unsafe archive names and failed record serialization leave no success output', () => {
  const root = mkdtempSync(join(tmpdir(), 'sdk-retention-test-'));
  try {
    const output = join(root, 'checked');
    expect(() => {
      retainCheckedPackage(
        output,
        'sdk.tgz',
        Buffer.from('different'),
        evidence,
      );
    }).toThrow('differs');
    expect(existsSync(output)).toBe(false);
    expect(() => {
      retainCheckedPackage(output, '../sdk.tgz', archive, evidence);
    }).toThrow('filename');
    expect(existsSync(output)).toBe(false);
    const cyclic: Record<string, unknown> = { ...evidence };
    cyclic.self = cyclic;
    expect(() => {
      retainCheckedPackage(output, 'sdk.tgz', archive, cyclic);
    }).toThrow();
    expect(existsSync(output)).toBe(false);
    retainCheckedPackage(output, 'sdk.tgz', archive, evidence);
    expect(readFileSync(join(output, 'sdk.tgz'))).toEqual(archive);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
