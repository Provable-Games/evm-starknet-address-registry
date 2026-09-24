import assert from 'node:assert/strict';

export interface CoverageCounters {
  readonly statementMap: Record<string, unknown>;
  readonly branchMap: Record<
    string,
    { readonly locations: readonly unknown[] }
  >;
  readonly fnMap: Record<string, unknown>;
  readonly s: Record<string, number>;
  readonly b: Record<string, number[]>;
  readonly f: Record<string, number>;
}
/** Counter completeness is distinct from whether every mapped outcome was covered. */
export function checkCoverageCounters(report: CoverageCounters): number[] {
  for (const [map, counters] of [
    [report.statementMap, report.s],
    [report.branchMap, report.b],
    [report.fnMap, report.f],
  ] as const) {
    assert.deepEqual(
      Object.keys(counters).sort(),
      Object.keys(map).sort(),
      'Coverage map and counter keys differ',
    );
  }
  for (const [key, branch] of Object.entries(report.branchMap)) {
    const counts = report.b[key];
    assert.ok(Array.isArray(counts), 'Missing branch counter array');
    assert.ok(Array.isArray(branch.locations), 'Missing branch locations');
    assert.equal(
      counts.length,
      branch.locations.length,
      'Branch counter arity differs',
    );
    for (let index = 0; index < counts.length; index++)
      assert.ok(Object.hasOwn(counts, index), 'Sparse branch counter array');
  }
  const counters = [
    ...Object.values(report.f),
    ...Object.values(report.s),
    ...Object.values(report.b).flat(),
  ];
  assert.ok(
    counters.every((count) => Number.isSafeInteger(count) && count >= 0),
    'Coverage counters must be finite nonnegative safe integers',
  );
  return counters;
}
