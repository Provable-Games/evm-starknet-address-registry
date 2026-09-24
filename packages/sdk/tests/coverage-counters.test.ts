import { expect, test } from 'vitest';
import { checkFunctionAttribution } from '../../../scripts/sdk-function-inventory.ts';
import { checkCoverageCounters } from '../../../scripts/sdk-coverage-counters.ts';
import type { CoverageCounters } from '../../../scripts/sdk-coverage-counters.ts';

function report(): CoverageCounters {
  return {
    statementMap: { '0': {}, '1': {} },
    branchMap: { '0': { locations: [{}, {}] } },
    fnMap: { '0': {} },
    s: { '0': 1, '1': 2 },
    b: { '0': [1, 3] },
    f: { '0': 1 },
  };
}
test('coverage integrity rejects omitted, renamed, truncated, and malformed counters', () => {
  expect(checkCoverageCounters(report())).toEqual([1, 1, 2, 1, 3]);
  const corruptions: ((value: CoverageCounters) => void)[] = [
    (value) => {
      delete value.s['0'];
    },
    (value) => {
      delete value.b['0'];
    },
    (value) => {
      delete value.f['0'];
      value.f.renamed = 1;
    },
    (value) => {
      value.s.extra = 1;
    },
    (value) => {
      value.b['0'] = [1];
    },
    (value) => {
      value.b['0'] = [1, 1, 1];
    },
    (value) => {
      value.b['0'] = [1, 1];
      Reflect.deleteProperty(value.b['0'], 1);
    },
    (value) => {
      value.b['0'] = 1 as unknown as number[];
    },
    (value) => {
      value.branchMap['0'] = { locations: undefined as unknown as unknown[] };
    },
  ];
  for (const corrupt of corruptions) {
    const value = report();
    corrupt(value);
    expect(() => checkCoverageCounters(value)).toThrow();
  }
  for (const bad of [NaN, Infinity, -1, 0.5, Number.MAX_SAFE_INTEGER + 1]) {
    for (const kind of ['s', 'f', 'b'] as const) {
      const value = report();
      if (kind === 'b') value.b['0'] = [1, bad];
      else value[kind]['0'] = bad;
      expect(() => checkCoverageCounters(value)).toThrow();
    }
  }
});

// Function declarations and parenthesized object arrows use these body positions
// in the real V8 report; declaration names/anonymous numbering are not identities.
test('function attribution rejects duplicated locations without changing positive counters or counts', () => {
  const source =
    'function first() { return 1; }\nconst second = () => ({ value: 2 });';
  const mapping = {
    '0': {
      name: 'first',
      decl: { start: { line: 1, column: 9 } },
      loc: { start: { line: 1, column: 17 } },
    },
    '1': {
      name: '(anonymous_1)',
      decl: { start: { line: 2, column: 15 } },
      loc: { start: { line: 2, column: 22 } },
    },
  };
  const value = report();
  Object.assign(value.fnMap, mapping);
  value.f['1'] = 1;
  expect(() => {
    checkFunctionAttribution('fixture.ts', source, value.fnMap);
  }).not.toThrow();
  value.fnMap['1'] = structuredClone(mapping['0']);
  expect(checkCoverageCounters(value)).toEqual([1, 1, 1, 2, 1, 3]);
  expect(Object.keys(value.fnMap)).toHaveLength(2);
  expect(() => {
    checkFunctionAttribution('fixture.ts', source, value.fnMap);
  }).toThrow('Duplicate function mapping');
  for (const invalid of [
    null,
    {},
    { loc: null },
    { loc: {} },
    { loc: { start: null } },
    { loc: { start: { line: 2, column: null } } },
    { loc: { start: { line: 2, column: -1 } } },
    { loc: { start: { line: 2, column: 23 } } },
  ]) {
    value.fnMap['1'] = invalid;
    expect(() => {
      checkFunctionAttribution('fixture.ts', source, value.fnMap);
    }).toThrow();
  }
  delete value.fnMap['1'];
  expect(() => {
    checkFunctionAttribution('fixture.ts', source, value.fnMap);
  }).toThrow('Unmapped or unmatched');
});
