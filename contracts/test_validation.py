"""Negative coverage-gate fixtures use synthetic files, never production approval."""
import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from check_coverage import check, authored_functions, validate_policy


class CoverageGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / 'contracts/src/registry.cairo'
        source.parent.mkdir(parents=True)
        source.write_text("fn work() { do_work(); }\nfn get_version() { '1' }\n")
        excluded = self.root / 'contracts/src/interface.cairo'
        excluded.write_text('pub struct Input { value: felt252 }\n')
        self.inventory = {
            'production_functions': {'contracts/src/registry.cairo': [
                {'function': 'fixture::work', 'mapped': True},
                {'function': 'fixture::get_version', 'mapped': False},
            ]},
            'excluded': {'contracts/src/interface.cairo': 'synthetic type only'},
            'excluded_source_sha256': {'contracts/src/interface.cairo': hashlib.sha256(excluded.read_bytes()).hexdigest()},
            'unmapped_exception_request': {
                'status': 'approved', 'function': 'fixture::get_version',
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            },
        }
        for items in self.inventory['production_functions'].values():
            for item in items:
                item.update(security=True, tests=['contracts/tests/test_fixture.cairo'])
        test = self.root / 'contracts/tests/test_fixture.cairo'
        test.parent.mkdir(parents=True)
        test.write_text('#[test] fn fixture() {}')
        self.policy = json.loads((Path(__file__).resolve().parents[1] / 'protocol/coverage-policy.json').read_text())
        self.policy['cairo']['planned_production_files'] = {'contracts/src/registry.cairo': 'security: synthetic fixture'}
        policy_path = self.root / 'protocol/coverage-policy.json'
        policy_path.parent.mkdir()
        policy_path.write_text(json.dumps(self.policy))
        self.report = f'SF:{source}\nFN:1,fixture::work\nFNDA:1,fixture::work\nDA:1,1\nLF:1\nLH:1\nFNF:1\nFNH:1\nend_of_record\n'

    def validate(self, report=None, inventory=None):
        return check(self.report if report is None else report,
                     self.inventory if inventory is None else inventory, self.root)

    def test_complete_synthetic_inventory(self):
        self.assertEqual(self.validate()['authored_functions'], 2)

    def test_missing_production_file(self):
        with self.assertRaisesRegex(ValueError, 'file omitted'):
            self.validate('')

    def test_zero_counter(self):
        for changed in [self.report.replace('DA:1,1', 'DA:1,0'),
                        self.report.replace('FNDA:1,', 'FNDA:0,')]:
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'summary counts|below 100%'):
                self.validate(changed)

    def test_stale_append(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.validate(self.report + self.report)

    def test_pending_exception_fails(self):
        inventory = copy.deepcopy(self.inventory)
        inventory['unmapped_exception_request']['status'] = 'pending'
        with self.assertRaisesRegex(ValueError, 'requires review'):
            self.validate(inventory=inventory)

    def test_new_function_fails(self):
        path = self.root / 'contracts/src/registry.cairo'
        path.write_text(path.read_text() + 'fn forgotten() {}\n')
        with self.assertRaisesRegex(ValueError, 'function inventory'):
            self.validate()

    def test_changed_constant_body_fails(self):
        path = self.root / 'contracts/src/registry.cairo'
        path.write_text(path.read_text().replace("'1'", "calculate()"))
        with self.assertRaisesRegex(ValueError, 'Exception source changed'):
            self.validate()

    def test_new_file_fails(self):
        (self.root / 'contracts/src/forgotten.cairo').write_text('fn ignored() {}')
        with self.assertRaisesRegex(ValueError, 'source inventory differs'):
            self.validate()

    def test_executable_code_in_excluded_file_fails(self):
        path = self.root / 'contracts/src/interface.cairo'
        path.write_text(path.read_text() + 'fn hidden_logic() {}')
        with self.assertRaisesRegex(ValueError, 'Excluded source changed'):
            self.validate()

    def test_deleted_line_counter_fails(self):
        with self.assertRaisesRegex(ValueError, 'summary counts'):
            self.validate(self.report.replace('DA:1,1\n', ''))

    def test_duplicate_records_fail(self):
        for record in ['DA:1,1', 'FN:1,fixture::work', 'FNDA:1,fixture::work', 'LF:1']:
            with self.subTest(record=record), self.assertRaisesRegex(ValueError, 'Duplicate LCOV'):
                self.validate(self.report.replace(record + '\n', record + '\n' + record + '\n'))

    def test_missing_or_wrong_summaries_fail(self):
        for record in ['LF:1', 'LH:1', 'FNF:1', 'FNH:1']:
            for replacement in ['', record[:-1] + '2\n']:
                with self.subTest(record=record), self.assertRaisesRegex(ValueError, 'summary counts'):
                    self.validate(self.report.replace(record + '\n', replacement))

    def test_counter_outside_source_fails(self):
        with self.assertRaisesRegex(ValueError, 'outside source'):
            self.validate(self.report.replace('DA:1,1', 'DA:100,1'))

    def test_missing_function_counter_fails(self):
        with self.assertRaisesRegex(ValueError, 'declarations and counters'):
            self.validate(self.report.replace('FNDA:1,fixture::work\n', ''))


    def test_restricted_visibility_and_modifier_functions_cannot_hide(self):
        for declaration in ['pub(crate) fn forgotten() {}', 'const fn forgotten() {}']:
            with self.subTest(declaration=declaration):
                path = self.root / 'contracts/src/registry.cairo'
                path.write_text("fn work() {}\nfn get_version() {}\n" + declaration)
                with self.assertRaisesRegex(ValueError, 'function inventory'):
                    self.validate()

    def test_generic_function_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'Unrecognized authored function'):
            authored_functions('fn forgotten<T>(x: T) -> T { x }')

    def test_comment_and_string_function_text_is_not_code(self):
        self.assertEqual(authored_functions("""// fn false_positive<T>() {}
            /* outer /* fn nested() {} */ fn comment() {} */
            fn real() { let a = "fn fake<T>() {}"; let b = 'fn text'; }
            trait Api { fn declaration(self: @T); }
        """), ['real'])

    def test_policy_threshold_and_classification_drift_fails(self):
        for group, key, value in [('global_and_per_file', 'mapped_lines', 94),
                                  ('security', 'reliably_mapped_lines', 99)]:
            policy = copy.deepcopy(self.policy)
            policy['cairo'][group][key] = value
            with self.assertRaisesRegex(ValueError, 'Frozen Cairo coverage policy'):
                validate_policy(policy, self.inventory)
        policy = copy.deepcopy(self.policy)
        policy['cairo']['planned_production_files']['contracts/src/forgotten.cairo'] = 'security: forgotten'
        with self.assertRaisesRegex(ValueError, 'classification differs'):
            validate_policy(policy, self.inventory)
        inventory = copy.deepcopy(self.inventory)
        inventory['production_functions']['contracts/src/registry.cairo'][0]['security'] = False
        with self.assertRaisesRegex(ValueError, 'classification differs'):
            validate_policy(self.policy, inventory)

    def test_resource_only_pointer_cannot_replace_coverage_pointer(self):
        inventory = copy.deepcopy(self.inventory)
        inventory['production_functions']['contracts/src/registry.cairo'][0]['tests'] = ['contracts/tests/test_resources.cairo']
        (self.root / 'contracts/tests/test_resources.cairo').write_text('#[test] fn resource() {}')
        with self.assertRaisesRegex(ValueError, 'absent or skipped'):
            self.validate(inventory=inventory)

    def test_function_filter_rejects_skipped_only_file_and_helpers(self):
        path = self.root / 'contracts/tests/test_fixture.cairo'
        for source in [
                '#[test] fn seeded_state_machine() {}',
                '#[test] #[fuzzer] fn seeded_state_machine(value: u128) {}\nfn helper() {}',
                '// #[test] fn fake() {}\nfn helper() { let s = "#[test] fn fake() {}"; }',
                '#[test] #[ignore] fn ignored() {}']:
            with self.subTest(source=source):
                path.write_text(source)
                with self.assertRaisesRegex(ValueError, 'no eligible tests'):
                    self.validate()

    def test_mixed_file_reports_only_selected_deterministic_functions(self):
        path = self.root / 'contracts/tests/test_fixture.cairo'
        path.write_text("""
            fn helper() {}
            #[test] #[fuzzer] fn seeded_state_machine(value: u128) {}
            #[test] #[ignore] fn ignored() {}
            #[feature("safe_dispatcher")] #[test] fn deterministic() {}
        """)
        inventory = copy.deepcopy(self.inventory)
        inventory['production_functions']['contracts/src/registry.cairo'][0]['fuzz_tests'] = ['contracts/tests/test_fixture.cairo']
        result = self.validate(inventory=inventory)['test_evidence']
        self.assertEqual(result['deterministic'][str(path.relative_to(self.root))],
                         ['contracts_integrationtest::test_fixture::deterministic'])
        self.assertEqual(result['fuzz'][str(path.relative_to(self.root))],
                         ['contracts_integrationtest::test_fixture::seeded_state_machine'])

    def test_unrecognized_test_syntax_or_conditional_attribute_fails_closed(self):
        path = self.root / 'contracts/tests/test_fixture.cairo'
        for source in ['#[test] fn generic<T>() {}', '#[cfg(anything)] #[test] fn conditional() {}',
                       'mod nested { #[test] fn nested_test() {} }']:
            with self.subTest(source=source):
                path.write_text(source)
                with self.assertRaisesRegex(ValueError, 'syntax|attribute'):
                    self.validate()

    def test_fuzz_pointer_requires_actual_skipped_fuzzer(self):
        inventory = copy.deepcopy(self.inventory)
        inventory['production_functions']['contracts/src/registry.cairo'][0]['fuzz_tests'] = ['contracts/tests/test_fixture.cairo']
        with self.assertRaisesRegex(ValueError, 'fuzz test pointer has no eligible tests'):
            self.validate(inventory=inventory)

    def test_improved_mapping_requires_explicit_recalibration(self):
        report = self.report.replace('LF:1', 'FN:2,fixture::get_version\nFNDA:1,fixture::get_version\nLF:1').replace('FNF:1', 'FNF:2').replace('FNH:1', 'FNH:2')
        with self.assertRaisesRegex(ValueError, 'now maps; review calibration'):
            self.validate(report)


class ResourceInventoryTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent
        self.cases = json.loads((root / 'resource-cases.json').read_text())
        self.source = (root / 'tests/test_resources.cairo').read_text()

    def validate(self, cases=None, source=None):
        from check_resources import validate_inventory
        validate_inventory(self.cases if cases is None else cases,
                           self.source if source is None else source)

    def test_reviewed_56_cases_match_authored_tests(self):
        self.validate()
        self.assertEqual(len(self.cases), 56)

    def test_empty_inventory_fails_before_trace_reads(self):
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            self.validate([])

    def test_missing_inventory_entry_fails(self):
        with self.assertRaisesRegex(ValueError, 'authored resource test'):
            self.validate(self.cases[1:])

    def test_duplicate_inventory_entry_fails(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.validate(self.cases + [self.cases[0]])

    def test_deleting_case_and_authored_test_still_fails(self):
        name = self.cases[0]['name']
        source = self.source.replace('fn ' + name + '(', 'fn removed_case(')
        with self.assertRaisesRegex(ValueError, 'policy axes'):
            self.validate(self.cases[1:], source)

    def test_policy_axis_mutation_fails(self):
        cases = copy.deepcopy(self.cases)
        cases[-1]['expected'] = 'success'
        with self.assertRaisesRegex(ValueError, 'policy axes') as raised:
            self.validate(cases)
        from check_resources import CASE_INVENTORY_SHA256
        canonical = json.dumps(cases, sort_keys=True, separators=(',', ':')).encode()
        self.assertIn(f'expected {CASE_INVENTORY_SHA256}', str(raised.exception))
        self.assertIn(f'computed {hashlib.sha256(canonical).hexdigest()}', str(raised.exception))

    def test_test_body_changed_without_inventory_fails(self):
        source = self.source.replace('"Loot Survivor"', '"A"', 1)
        with self.assertRaisesRegex(ValueError, 'test source changed') as raised:
            self.validate(source=source)
        from check_resources import CASE_TEST_SOURCE_SHA256
        self.assertIn(f'expected {CASE_TEST_SOURCE_SHA256}', str(raised.exception))
        self.assertIn(f'computed {hashlib.sha256(source.encode()).hexdigest()}', str(raised.exception))

    def test_helper_scenario_mutation_fails(self):
        from check_resources import validate_inventory, CASE_HELPER_SOURCE_SHA256
        source = (Path(__file__).resolve().parent / 'tests/resource_helpers.cairo').read_text()
        mutated = source.replace('index == position', 'index == 0')
        self.assertNotEqual(mutated, source)
        with self.assertRaisesRegex(ValueError, 'helper source changed') as raised:
            validate_inventory(self.cases, self.source, mutated)
        self.assertIn(CASE_HELPER_SOURCE_SHA256, str(raised.exception))
        self.assertIn(hashlib.sha256(mutated.encode()).hexdigest(), str(raised.exception))


class EvidenceFailureTests(unittest.TestCase):
    def test_failed_invocations_preserve_fresh_traces_and_original_error(self):
        import run_evidence
        for mode, failure_index, relative in [('coverage', 1, 'traces'),
                                              ('resources', 1, 'gas/traces'),
                                              ('resources', 2, 'steps/traces')]:
            with self.subTest(mode=mode, failure_index=failure_index), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                contracts = root / 'contracts'
                trace_dir = contracts / 'snfoundry_trace'
                trace_dir.mkdir(parents=True)
                (trace_dir / 'old.json').write_text('old evidence')
                output = root / 'evidence'
                failure = subprocess.CalledProcessError(7, ['snforge', 'test'])
                invocations = 0

                def failed_run(command, log, env):
                    nonlocal invocations
                    invocations += 1
                    trace_dir.mkdir()
                    (trace_dir / 'fresh.json').write_text(f'trace {invocations}')
                    log.write_text('failed run' if invocations == failure_index else 'passed run')
                    if invocations == failure_index:
                        raise failure

                with mock.patch.multiple(run_evidence, ROOT=root, CONTRACTS=contracts), \
                     mock.patch.object(run_evidence, 'source_identity', side_effect=[{'source': 'before'}, {'source': 'after'}]), \
                     mock.patch.object(run_evidence, 'run', side_effect=failed_run), \
                     mock.patch('sys.argv', ['run_evidence.py', mode, '--output', str(output)]):
                    with self.assertRaises(subprocess.CalledProcessError) as raised:
                        run_evidence.main()
                self.assertIs(raised.exception, failure)
                self.assertIn('Source changed', failure.__notes__[0])
                self.assertFalse(trace_dir.exists())
                fresh = output / relative / 'fresh.json'
                self.assertEqual(fresh.read_text(), f'trace {failure_index}')
                inventory = json.loads((output / 'evidence-sha256.json').read_text())
                self.assertEqual(inventory[f'{relative}/fresh.json'], hashlib.sha256(fresh.read_bytes()).hexdigest())
                self.assertFalse(any('prior-traces' in name for name in inventory))
                self.assertEqual((output / 'prior-traces-not-measured/old.json').read_text(), 'old evidence')
                if failure_index == 2:
                    self.assertEqual((output / 'gas/traces/fresh.json').read_text(), 'trace 1')
                    self.assertIn('gas/traces/fresh.json', inventory)


if __name__ == '__main__':
    unittest.main()
