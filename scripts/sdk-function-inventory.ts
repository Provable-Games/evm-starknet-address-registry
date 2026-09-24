import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import ts from 'typescript';

export interface FunctionPosition {
  readonly name: string;
  readonly line: number;
  readonly column: number;
}
export type FunctionInventory = Record<string, FunctionPosition[]>;
export function sourceFunctions(
  file: string,
  text: string,
): FunctionPosition[] {
  const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true);
  const functions: FunctionPosition[] = [];
  function visit(node: ts.Node): void {
    if (
      (ts.isArrowFunction(node) ||
        ts.isFunctionExpression(node) ||
        ts.isFunctionDeclaration(node) ||
        ts.isMethodDeclaration(node)) &&
      node.body
    ) {
      const position = source.getLineAndCharacterOfPosition(
        node.getStart(source),
      );
      functions.push({
        name: node.name?.getText(source) ?? '(anonymous)',
        line: position.line + 1,
        column: position.character + 1,
      });
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  return functions;
}
/** V8 maps function bodies, and omits parentheses around expression bodies. */
export function checkFunctionAttribution(
  file: string,
  text: string,
  fnMap: Record<string, unknown>,
): void {
  const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true);
  const expected: string[] = [];
  function visit(node: ts.Node): void {
    if (
      (ts.isArrowFunction(node) ||
        ts.isFunctionExpression(node) ||
        ts.isFunctionDeclaration(node) ||
        ts.isMethodDeclaration(node)) &&
      node.body
    ) {
      let body: ts.Node = node.body;
      while (ts.isParenthesizedExpression(body)) body = body.expression;
      const position = source.getLineAndCharacterOfPosition(
        body.getStart(source),
      );
      expected.push(
        `${String(position.line + 1)}:${String(position.character)}`,
      );
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  const actual = Object.values(fnMap).map((entry) => {
    assert.ok(
      typeof entry === 'object' && entry !== null,
      'Malformed function mapping',
    );
    const loc: unknown = Reflect.get(entry, 'loc');
    assert.ok(
      typeof loc === 'object' && loc !== null,
      'Missing function location',
    );
    const start: unknown = Reflect.get(loc, 'start');
    assert.ok(
      typeof start === 'object' && start !== null,
      'Missing function body start',
    );
    const line: unknown = Reflect.get(start, 'line');
    const column: unknown = Reflect.get(start, 'column');
    assert.ok(
      typeof line === 'number' &&
        Number.isSafeInteger(line) &&
        line > 0 &&
        typeof column === 'number' &&
        Number.isSafeInteger(column) &&
        column >= 0,
      'Malformed function body position',
    );
    return `${String(line)}:${String(column)}`;
  });
  assert.equal(
    new Set(expected).size,
    expected.length,
    `Ambiguous source function bodies: ${file}`,
  );
  assert.equal(
    new Set(actual).size,
    actual.length,
    `Duplicate function mapping: ${file}`,
  );
  assert.deepEqual(
    actual.sort(),
    expected.sort(),
    `Unmapped or unmatched executable function: ${file}`,
  );
}
/** Explicit regeneration updates positions only; callers must check source classification first. */
export function checkFunctionInventory(
  path: string,
  actual: FunctionInventory,
  write: boolean,
): void {
  if (write) writeFileSync(path, JSON.stringify(actual, null, 2) + '\n');
  else
    assert.deepEqual(
      JSON.parse(readFileSync(path, 'utf8')),
      actual,
      'Function inventory drift; run node scripts/check-sdk-coverage.ts --write after reviewing source changes',
    );
}
