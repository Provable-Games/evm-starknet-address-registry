"""Audit production LCOV against the reviewed function inventory; missing code fails."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


# Shared with collection so resource-only pointers cannot masquerade as coverage.
COVERAGE_SKIPS = ('seeded_state_machine', 'test_resources')


def source_tokens(source):
    """Remove comments and strings before examining authored Cairo syntax."""
    clean = []
    index = 0
    while index < len(source):
        if source.startswith('//', index):
            end = source.find('\n', index)
            index = len(source) if end < 0 else end
            clean.append(' ')
        elif source.startswith('/*', index):
            depth = 1
            index += 2
            while index < len(source) and depth:
                if source.startswith('/*', index):
                    depth += 1
                    index += 2
                elif source.startswith('*/', index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth:
                raise ValueError('Unterminated source comment')
            clean.append(' ')
        elif source[index] in ('"', "'"):
            quote = source[index]
            index += 1
            while index < len(source) and source[index] != quote:
                index += 2 if source[index] == '\\' else 1
            if index >= len(source):
                raise ValueError('Unterminated source string')
            index += 1
            clean.append(' ')
        else:
            clean.append(source[index])
            index += 1
    return ''.join(clean)


def authored_functions(source):
    """Conservative lexical scan: every fn token must parse or fail closed."""
    text = source_tokens(source)
    functions = []
    for token in re.finditer(r'\bfn\b', text):
        declaration = re.match(r'fn\s+(\w+)\s*\([^;{]*?\)\s*(?:->[^;{]*)?([;{])', text[token.start():])
        if declaration is None:
            raise ValueError('Unrecognized authored function syntax; explicit parser review required')
        if declaration[2] == '{':
            functions.append(declaration[1])
    return functions


def validate_policy(policy, inventory):
    cairo = policy['cairo']
    frozen = {
        'global_and_per_file': {'mapped_lines': 95, 'mapped_functions': 100},
        'security': {'reliably_mapped_lines': 100, 'reliably_mapped_functions': 100,
                     'explicit_outcome_inventory': True},
        'branch_percentage': None,
        'type_only_files': [],
    }
    if any(cairo.get(key) != value for key, value in frozen.items()):
        raise ValueError('Frozen Cairo coverage policy differs; explicit policy/gate review required')
    classifications = cairo['planned_production_files']
    if set(classifications) != set(inventory['production_functions']) or any(
            not value.startswith('security: ') for value in classifications.values()) or any(
            item.get('security') is not True for items in inventory['production_functions'].values() for item in items):
        raise ValueError('Cairo policy source/security classification differs from enforced inventory')


def test_functions(path, root):
    """Recognize top-level #[test] functions; reject unsupported test syntax."""
    source = root / path
    if source.parent != root / 'contracts/tests' or not source.is_file():
        raise ValueError('Coverage test pointer is absent or outside integration tests')
    text = source_tokens(source.read_text())
    if re.search(r'\bmod\s', text):
        raise ValueError('Nested test module syntax requires explicit collector review')
    pattern = r'((?:#\s*\[[^\[\]]*\]\s*)+)fn\s+(\w+)\s*\(([^)]*)\)\s*\{'
    tests = []
    recognized = 0
    for match in re.finditer(pattern, text):
        attributes = re.findall(r'#\s*\[\s*(\w+)', match[1])
        if 'test' not in attributes:
            continue
        recognized += attributes.count('test')
        if set(attributes) - {'test', 'fuzzer', 'feature', 'ignore', 'should_panic', 'available_gas'}:
            raise ValueError('Unsupported test attribute requires explicit collector review')
        function = 'contracts_integrationtest::' + source.stem + '::' + match[2]
        tests.append({'function': function, 'fuzz': 'fuzzer' in attributes or bool(match[3].strip()),
                      'ignored': 'ignore' in attributes,
                      'skipped': any(skip in function for skip in COVERAGE_SKIPS)})
    if recognized != len(re.findall(r'#\s*\[\s*test\s*\]', text)):
        raise ValueError('Unrecognized authored test syntax requires explicit collector review')
    return tests


def validate_test_references(inventory, root):
    selected = {'deterministic': {}, 'fuzz': {}, 'resource': {}}
    for items in inventory['production_functions'].values():
        for item in items:
            if not item.get('tests'):
                raise ValueError('Missing deterministic coverage test pointers')
            for field, category in [('tests', 'deterministic'), ('fuzz_tests', 'fuzz'),
                                    ('resource_tests', 'resource')]:
                for path in item.get(field, []):
                    if path in selected[category]:
                        continue
                    tests = test_functions(path, root)
                    if category == 'deterministic':
                        eligible = [test for test in tests if not test['fuzz'] and not test['ignored']
                                    and not test['skipped']]
                    elif category == 'fuzz':
                        eligible = [test for test in tests if test['fuzz'] and not test['ignored']
                                    and test['skipped']]
                    else:
                        eligible = [test for test in tests if path == 'contracts/tests/test_resources.cairo'
                                    and not test['fuzz'] and not test['ignored'] and test['skipped']]
                    if not eligible:
                        raise ValueError(f'{category} test pointer has no eligible tests (absent or skipped): {path}')
                    selected[category][path] = [test['function'] for test in eligible]
    return selected


def parse_record(lines, source):
    """Check every emitted production counter before computing a percentage."""
    line_count = len(source.splitlines())
    line_hits, function_hits, declarations, summaries = {}, {}, {}, {}
    for record in lines:
        kind, _, value = record.partition(':')
        if kind == 'DA':
            fields = value.split(',')
            if len(fields) not in (2, 3):
                raise ValueError('Malformed LCOV line counter')
            number, hits = int(fields[0]), int(fields[1])
            if number in line_hits:
                raise ValueError('Duplicate LCOV line counter')
            if not 1 <= number <= line_count or hits < 0:
                raise ValueError('LCOV line counter outside source or negative')
            line_hits[number] = hits
        elif kind == 'FN':
            number, function = value.split(',', 1)
            if function in declarations:
                raise ValueError('Duplicate LCOV function declaration')
            if not 1 <= int(number) <= line_count or not function:
                raise ValueError('LCOV function declaration outside source')
            declarations[function] = int(number)
        elif kind == 'FNDA':
            hits, function = value.split(',', 1)
            if function in function_hits:
                raise ValueError('Duplicate LCOV function counter')
            if int(hits) < 0 or not function:
                raise ValueError('Invalid LCOV function counter')
            function_hits[function] = int(hits)
        elif kind in {'LF', 'LH', 'FNF', 'FNH'}:
            if kind in summaries:
                raise ValueError('Duplicate LCOV summary')
            summaries[kind] = int(value)
    if set(declarations) != set(function_hits):
        raise ValueError('LCOV function declarations and counters differ')
    expected_summaries = {
        'LF': len(line_hits), 'LH': sum(hits > 0 for hits in line_hits.values()),
        'FNF': len(declarations), 'FNH': sum(hits > 0 for hits in function_hits.values()),
    }
    if summaries != expected_summaries:
        raise ValueError('LCOV summary counts differ from complete counter records')
    if not line_hits or not function_hits:
        raise ValueError('Empty production denominator')
    return line_hits, function_hits


def check(report, inventory, root=ROOT):
    validate_policy(json.loads((root / 'protocol/coverage-policy.json').read_text()), inventory)
    test_evidence = validate_test_references(inventory, root)
    expected_files = set(inventory['production_functions'])
    all_sources = {p.relative_to(root).as_posix() for p in (root/'contracts/src').rglob('*.cairo')}
    if all_sources != expected_files | set(inventory['excluded']):
        raise ValueError('Production source inventory differs; new files require classification')
    for name in inventory['excluded']:
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != inventory['excluded_source_sha256'][name]:
            raise ValueError(f'Excluded source changed; review executable-code classification: {name}')
    expected = {item['function']: (name, item) for name, items in inventory['production_functions'].items() for item in items}
    for name, items in inventory['production_functions'].items():
        declarations = authored_functions((root/name).read_text())
        if sorted(declarations) != sorted(item['function'].split('::')[-1] for item in items):
            raise ValueError(f'Authored function inventory differs: {name}')
    exception = inventory['unmapped_exception_request']
    if hashlib.sha256((root/'contracts/src/registry.cairo').read_bytes()).hexdigest() != exception['source_sha256']:
        raise ValueError('Exception source changed; review the constant-only function again')
    seen_files, seen_functions, counts = set(), set(), {}
    for block in report.split('end_of_record'):
        lines = block.strip().splitlines()
        sources = [x[3:] for x in lines if x.startswith('SF:')]
        if len(sources) > 1:
            raise ValueError('Multiple LCOV source records in one block')
        sf = sources[0] if sources else None
        if not sf:
            continue
        try:
            name = Path(sf).resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        if name not in expected_files:
            continue
        if name in seen_files:
            raise ValueError('Duplicate LCOV production file; stale/appended reports are forbidden')
        seen_files.add(name)
        line_hits, function_hits = parse_record(lines, (root/name).read_text())
        if any(value <= 0 for value in line_hits.values()) or any(value <= 0 for value in function_hits.values()):
            raise ValueError(f'Security coverage below 100%: {name}')
        if any(function not in expected or expected[function][0] != name for function in function_hits):
            raise ValueError('Unexpected function attribution; macro filtering or inventory needs review')
        seen_functions.update(function_hits)
        counts[name] = {'mapped_lines': len(line_hits), 'hit_lines': len(line_hits), 'mapped_functions': len(function_hits), 'hit_functions': len(function_hits)}
    if seen_files != expected_files:
        raise ValueError('Required production file omitted from LCOV')
    if not set(expected)-seen_functions:
        raise ValueError('Previously unmapped constant function now maps; review calibration and remove exception')
    if set(expected)-seen_functions != {exception['function']}:
        raise ValueError('Missing authored functions beyond the single reviewed constant-body exception')
    if any(not item['mapped'] for name,item in expected.values() if item['function'] != exception['function']):
        raise ValueError('Unreviewed mapping exclusion')
    if exception['status'] != 'approved':
        raise ValueError('The specific unmapped-function exception still requires review')
    return {'test_evidence':test_evidence,'files':counts,'authored_functions':len(expected),'mapped_functions':len(seen_functions),'unmapped_constant_function':exception['function'],'branch_coverage':None}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('report',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=check(args.report.read_text(),json.loads((ROOT/'contracts/production-inventory.json').read_text()))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Production mapped security coverage 100%; complete authored inventory reconciled')

if __name__=='__main__':main()
