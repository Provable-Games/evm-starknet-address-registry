import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';

/** Publish only checked public bytes; a newly created destination is rolled back on failure. */
export function retainCheckedPackage(
  output: string,
  filename: string,
  archive: Uint8Array,
  evidence: Record<string, unknown>,
): void {
  assert.ok(
    filename === basename(filename) && filename.endsWith('.tgz'),
    'Invalid archive filename',
  );
  const sha256 = createHash('sha256').update(archive).digest('hex');
  assert.equal(
    sha256,
    evidence.archive_sha256,
    'Retained archive differs from checked archive',
  );
  // mkdir without recursive is exclusive, including existing files and dangling symlinks.
  mkdirSync(output, { mode: 0o700 });
  try {
    writeFileSync(join(output, filename), archive, { flag: 'wx', mode: 0o600 });
    writeFileSync(
      join(output, 'checked-package.json'),
      JSON.stringify(
        {
          schema_version: 1,
          kind: 'local-checked-sdk-pack',
          archive: { filename, bytes: archive.byteLength, sha256 },
          evidence,
        },
        null,
        2,
      ) + '\n',
      { flag: 'wx', mode: 0o600 },
    );
  } catch (cause) {
    rmSync(output, { recursive: true, force: true });
    throw cause;
  }
}
