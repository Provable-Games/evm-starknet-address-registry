import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  sourceFunctions,
  checkFunctionInventory,
  checkFunctionAttribution,
} from './sdk-function-inventory.ts';
import type { FunctionInventory } from './sdk-function-inventory.ts';
import { checkCoverageCounters } from './sdk-coverage-counters.ts';
import type { CoverageCounters } from './sdk-coverage-counters.ts';

const root = resolve(import.meta.dirname, '..');
const args = process.argv.slice(2);
assert.ok(
  args.length === 0 || (args.length === 1 && args[0] === '--write'),
  'Usage: node scripts/check-sdk-coverage.ts [--write]',
);
const write = args[0] === '--write';
const policy = JSON.parse(
  readFileSync(resolve(root, 'protocol/coverage-policy.json'), 'utf8'),
) as {
  sdk: {
    planned_production_files: Record<string, string>;
    type_only_files: string[];
    runtime_enforcement: Record<string, number>;
  };
};
const files = readdirSync(resolve(root, 'packages/sdk/src'))
  .filter((file) => file.endsWith('.ts'))
  .map((file) => `packages/sdk/src/${file}`)
  .sort();
assert.deepEqual(
  files,
  [
    ...Object.keys(policy.sdk.planned_production_files),
    ...policy.sdk.type_only_files,
  ].sort(),
  'Every SDK source must have frozen classification',
);
assert.deepEqual(policy.sdk.runtime_enforcement, {
  statements: 100,
  lines: 100,
  branches: 100,
  functions: 100,
});
const inventory: FunctionInventory = Object.fromEntries(
  files.map((file) => [
    file,
    sourceFunctions(file, readFileSync(resolve(root, file), 'utf8')),
  ]),
);
checkFunctionInventory(
  resolve(root, 'packages/sdk/coverage-inventory.json'),
  inventory,
  write,
);
if (write) {
  process.stdout.write(
    'Regenerated SDK function positions; coverage and classification gates remain required.\n',
  );
  process.exit(0);
}
const coverage = JSON.parse(
  readFileSync(resolve(root, 'coverage/coverage-final.json'), 'utf8'),
) as Record<string, CoverageCounters>;
assert.deepEqual(
  Object.keys(coverage)
    .map((file) => file.slice(root.length + 1))
    .sort(),
  files,
  'Coverage must include all inventoried source files',
);
let totalFunctions = 0;
for (const file of files) {
  const functions = inventory[file];
  assert.ok(functions);
  const report = coverage[resolve(root, file)];
  assert.ok(report, `Missing raw coverage: ${file}`);
  assert.equal(
    Object.keys(report.fnMap).length,
    functions.length,
    `Unmapped executable function: ${file}`,
  );
  assert.equal(
    Object.keys(report.f).length,
    functions.length,
    `Missing function counters: ${file}`,
  );
  checkFunctionAttribution(
    file,
    readFileSync(resolve(root, file), 'utf8'),
    report.fnMap,
  );
  const counters = checkCoverageCounters(report);
  if (policy.sdk.type_only_files.includes(file))
    assert.equal(
      counters.length,
      0,
      'Type-only source gained executable behavior',
    );
  else
    assert.ok(
      Object.keys(report.s).length > 0,
      `Missing production denominator: ${file}`,
    );
  assert.ok(
    counters.every((count) => Number.isFinite(count) && count > 0),
    `Uncovered production outcome: ${file}`,
  );
  totalFunctions += functions.length;
}
process.stdout.write(
  `Audited ${String(files.length)} SDK files and ${String(totalFunctions)} executable functions; all raw counters covered.\n`,
);
