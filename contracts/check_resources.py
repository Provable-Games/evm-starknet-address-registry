"""Validate isolated registry-call resource traces and report explicit units/scopes."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


# Resource inventory revision 1: the 56 reviewed scenarios cover the policy axes
# without inventing impossible combinations (for example unlinking an empty set).
# Changes require explicit inventory/source review and a new measured baseline.
CASE_INVENTORY_SHA256 = '49ea7802d491f69049f071eb10073a78b8ce0d7306a2386c8da832cbf6e7f595'
CASE_TEST_SOURCE_SHA256 = '5dc79a0a1547e21e30e2ec1ad08916775ad1e98045ecc58cb41143edce5065ec'

CASE_HELPER_SOURCE_SHA256 = 'f5b5489b2acc98528f161d76c143e353daf95e9dd216f99cf224e4d0a9266d37'

def validate_inventory(cases, source, helper_source=None):
    if helper_source is None:
        helper_source = (ROOT / 'contracts/tests/resource_helpers.cairo').read_text()
    helper_sha256 = hashlib.sha256(helper_source.encode()).hexdigest()
    if helper_sha256 != CASE_HELPER_SOURCE_SHA256:
        raise ValueError('Reviewed resource helper source changed; reconcile scenarios and remeasure; '
                         f'expected {CASE_HELPER_SOURCE_SHA256}, computed {helper_sha256}')
    if not isinstance(cases, list) or not cases:
        raise ValueError('Resource inventory must be a nonempty list')
    names = []
    fields = {'name', 'operation', 'scenario', 'size', 'position', 'label_length', 'limit', 'expected'}
    for case in cases:
        if not isinstance(case, dict) or set(case) != fields:
            raise ValueError('Resource case fields differ from the reviewed schema')
        if not isinstance(case['name'], str) or not re.fullmatch(r'resource_[a-z0-9_]+', case['name']):
            raise ValueError('Invalid resource test function name')
        for field in ['size', 'position', 'label_length', 'limit']:
            if type(case[field]) is not int or case[field] < 0:
                raise ValueError(f'Invalid resource case integer: {field}')
        names.append(case['name'])
    if len(set(names)) != len(names):
        raise ValueError('Duplicate resource cases')
    authored = re.findall(r'^fn (resource_[a-z0-9_]+)\(', source, re.MULTILINE)
    if not authored or len(set(authored)) != len(authored) or set(authored) != set(names):
        raise ValueError('Resource inventory differs from authored resource test functions')
    canonical = json.dumps(cases, sort_keys=True, separators=(',', ':')).encode()
    inventory_sha256 = hashlib.sha256(canonical).hexdigest()
    if inventory_sha256 != CASE_INVENTORY_SHA256:
        raise ValueError('Reviewed resource inventory changed; required policy axes need explicit revision review; '
                         f'expected {CASE_INVENTORY_SHA256}, computed {inventory_sha256}')
    source_sha256 = hashlib.sha256(source.encode()).hexdigest()
    if source_sha256 != CASE_TEST_SOURCE_SHA256:
        raise ValueError('Reviewed resource test source changed; reconcile scenarios and remeasure; '
                         f'expected {CASE_TEST_SOURCE_SHA256}, computed {source_sha256}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gas', type=Path, required=True)
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads((ROOT / 'contracts/resource-cases.json').read_text())
    validate_inventory(cases, (ROOT / 'contracts/tests/test_resources.cairo').read_text())
    log = (args.gas / 'run.log').read_text()
    records = []
    for case in cases:
        row = dict(case)
        for mode, directory in [('gas', args.gas), ('steps', args.steps)]:
            paths = list((directory / 'traces').glob('*' + case['name'] + '.json'))
            if len(paths) != 1:
                raise ValueError(f'Missing/ambiguous trace: {case["name"]} {mode}')
            trace = json.loads(paths[0].read_text())
            calls = [item['EntryPointCall'] for item in trace['nested_calls'] if 'EntryPointCall' in item
                     and item['EntryPointCall']['entry_point']['function_name'] == case['operation']]
            if len(calls) != 1:
                raise ValueError(f'Expected exactly one measured registry call: {case["name"]} {mode}')
            resource = calls[0]['used_execution_resources']
            row[mode] = resource
        if row['steps']['vm_resources']['n_steps'] <= 0:
            raise ValueError('Missing positive Cairo-step measurement')
        for syscall in ['StorageRead', 'StorageWrite']:
            counts = [row[mode]['syscall_counter'].get(syscall, {}).get('call_count', 0)
                      for mode in ['gas', 'steps']]
            if counts[0] != counts[1]:
                raise ValueError('Storage work differs between resource measurement modes')
        block = next((part for part in log.split('[PASS] ') if part.startswith('contracts_integrationtest::test_resources::' + case['name'] + ' ')), None)
        if block is None:
            raise ValueError('Missing passing resource case in log')
        whole = re.search(r'l1_gas: ~(\d+), l1_data_gas: ~(\d+), l2_gas: ~(\d+)', block)
        if not whole:
            raise ValueError('Missing whole-test gas estimates')
        row['whole_test_estimate'] = dict(zip(['l1_gas', 'l1_data_gas', 'l2_gas'], map(int, whole.groups())))
        table = re.search(r'\| ' + re.escape(case['operation']) + r'\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|', block)
        if table:
            minimum, maximum, average, deviation, count = map(int, table.groups())
            if count != 1 or minimum != maximum or minimum != average or deviation:
                raise ValueError('Measured operation must have exactly one attributable call')
            row['operation_l2_gas_estimate'] = average
        elif case['expected'] == 'success':
            raise ValueError('Missing successful operation gas table')
        else:
            row['operation_l2_gas_estimate'] = None
        records.append(row)
    # Count-preserving invariance: last-element removal has a separately bounded cheaper path.
    for operation in ['link','move','unlink','revoke','invalidate_pending_incoming']:
        selected = [r for r in records if r['operation'] == operation and r['name'].endswith('_first') and r['size'] >= 2]
        groups = {}
        for row in selected:
            group = 'unlinked' if 'unlinked' in row['name'] else 'linked'
            counts = tuple(row['gas']['syscall_counter'].get(k, {}).get('call_count',0) for k in ['StorageRead','StorageWrite'])
            if group in groups and groups[group] != counts:
                raise ValueError(f'Storage work grows with membership size: {operation} {group}')
            groups[group] = counts
    for row in records:
        if row['operation'] == 'get_ethereum_addresses' and row['expected'] == 'success':
            reads = row['gas']['syscall_counter']['StorageRead']['call_count']
            if reads != 1 + min(row['size'], row['limit']):
                raise ValueError('Pagination must read count plus only returned entries')
    args.output.write_text(json.dumps({'profile':'dev','scope':'Each trace selects exactly one named registry call; whole-test estimates include constructor and fixture setup. Gas trace field gas_consumed is Sierra gas; operation_l2_gas_estimate is Foundry gas-report L2 estimate. No network fee claim. Reverted operation L2 table may be unavailable.','cases':records},indent=2)+'\n')
    print(f'Verified {len(records)} resource cases, constant mutation storage work and bounded pagination')

if __name__ == '__main__':
    main()
