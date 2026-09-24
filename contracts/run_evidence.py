"""Collect fresh deterministic traces, preserve raw evidence, then enforce attribution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from check_coverage import COVERAGE_SKIPS

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / 'contracts'


def run(command, log, env):
    with log.open('w') as output:
        output.write(json.dumps(command) + '\n')
        output.flush()
        with subprocess.Popen(command, cwd=CONTRACTS, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True) as process:
            for line in process.stdout:
                print(line, end='', flush=True)
                output.write(line)
                output.flush()
            status = process.wait()
    if status:
        raise subprocess.CalledProcessError(status, command)
    if command[:2] == ['snforge', 'test']:
        sys.path.insert(0, str(ROOT / 'scripts'))
        from run_cairo_tests import require_passing_tests
        require_passing_tests(log.read_text())


def source_identity():
    paths = sorted((CONTRACTS / 'src').rglob('*.cairo'))
    paths += sorted((CONTRACTS / 'tests').rglob('*.cairo'))
    paths += [CONTRACTS / 'Scarb.toml', CONTRACTS / 'Scarb.lock', ROOT / 'toolchain.json',
              ROOT / 'protocol/coverage-policy.json', CONTRACTS / 'production-inventory.json',
              CONTRACTS / 'resource-cases.json']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['coverage', 'resources'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = source_identity()
    (output / 'source-identity.json').write_text(json.dumps(before, indent=2) + '\n')
    env = dict(os.environ)
    env.pop('UNIVERSAL_SIERRA_COMPILER', None)
    env['PATH'] = str(ROOT / '.tools/bin') + ':/usr/bin:/bin'
    trace_dir = CONTRACTS / 'snfoundry_trace'
    # Retain prior output separately; never mix it with the new trace set.
    if trace_dir.exists():
        shutil.move(str(trace_dir), output / 'prior-traces-not-measured')
    trace_destination = output / 'traces'
    try:
        if args.mode == 'coverage':
            env['SCARB_TARGET_DIR'] = str(output / 'target')
            run(['snforge', 'test', '--profile', 'coverage', '--coverage', '--save-trace-data',
                 *[argument for skip in COVERAGE_SKIPS for argument in ('--skip', skip)],
                 '--color', 'never'], output / 'run.log', env)
            shutil.move(str(trace_dir), output / 'traces')
            shutil.copyfile(CONTRACTS / 'coverage/coverage.lcov', output / 'raw.lcov')
            traces = sorted(str(p) for p in (output / 'traces').glob('*.json'))
            if not traces:
                raise ValueError('No deterministic coverage traces')
            run(['cairo-coverage', 'run', *traces, '--output-path', str(output / 'no-macros.lcov'),
                 '--unstable', '--include'], output / 'mapping.log', env)
            run([sys.executable, str(CONTRACTS / 'check_coverage.py'), str(output / 'no-macros.lcov'),
                 '--output', str(output / 'audited.json')], output / 'gate.log', env)
        else:
            for mode, tracked in [('gas', 'sierra-gas'), ('steps', 'cairo-steps')]:
                directory = output / mode
                directory.mkdir()
                trace_destination = directory / 'traces'
                run(['snforge', 'test', 'test_resources', '--tracked-resource', tracked,
                     '--save-trace-data', '--detailed-resources', '--gas-report', '--color', 'never'],
                    directory / 'run.log', env)
                shutil.move(str(trace_dir), directory / 'traces')
            run([sys.executable, str(CONTRACTS / 'check_resources.py'), '--gas', str(output / 'gas'),
                 '--steps', str(output / 'steps'), '--output', str(output / 'audited.json')],
                output / 'gate.log', env)
    finally:
        # A failed Foundry run can still produce useful traces. Preserve them in
        # the same invocation directory and inventory them before propagating
        # the original failure (including failures during source verification).
        original_error = sys.exception()
        cleanup_errors = []
        try:
            if trace_dir.exists():
                shutil.move(str(trace_dir), trace_destination)
        except Exception as error:
            cleanup_errors.append(error)
        try:
            after = source_identity()
            if before != after:
                raise ValueError('Source changed during evidence collection')
        except Exception as error:
            cleanup_errors.append(error)
        try:
            artifacts = sorted(p for p in output.rglob('*') if p.is_file()
                               and 'target' not in p.relative_to(output).parts
                               and 'prior-traces-not-measured' not in p.relative_to(output).parts)
            (output / 'evidence-sha256.json').write_text(json.dumps({
                p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in artifacts}, indent=2) + '\n')
        except Exception as error:
            cleanup_errors.append(error)
        if original_error is not None:
            for error in cleanup_errors:
                original_error.add_note(f'Evidence finalization also failed: {error!r}')
        elif cleanup_errors:
            for error in cleanup_errors[1:]:
                cleanup_errors[0].add_note(f'Evidence finalization also failed: {error!r}')
            raise cleanup_errors[0]


if __name__ == '__main__':
    main()
