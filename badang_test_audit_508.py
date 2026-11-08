"""Run full offline suite; distinguish dependency/import failures from passing tests.

No network, DB access, orders, or credential output. Exit nonzero unless all tests pass.
"""
import argparse
import contextlib
import io
import json
from pathlib import Path
import re
import unittest


class _BoundedSink(io.TextIOBase):
    """Discard noisy test output without retaining credentials or unbounded logs."""
    def __init__(self):
        self.characters_discarded = 0

    def write(self, value):
        if not isinstance(value, str):
            raise TypeError('text output expected')
        self.characters_discarded += len(value)
        return len(value)

    def flush(self):
        pass


def audit(start_dir='.', pattern='test*.py', loader=None, runner=None):
    result = {'status': 'TESTS_INCOMPLETE', 'tests_run': 0, 'failures': 0,
              'errors': 0, 'skipped': 0, 'read_only': True,
              'trading_ready': False, 'missing_dependencies': []}
    try:
        # Discovery and tests may print operational messages. Keep CI output
        # limited to the sanitized result, even when a test is noisy.
        with contextlib.redirect_stdout(_BoundedSink()), contextlib.redirect_stderr(_BoundedSink()):
            suite = (loader or unittest.defaultTestLoader).discover(start_dir, pattern=pattern)
            stream = _BoundedSink()
            outcome = (runner or unittest.TextTestRunner(stream=stream, verbosity=0)).run(suite)
        result.update(tests_run=outcome.testsRun, failures=len(outcome.failures),
                      errors=len(outcome.errors), skipped=len(outcome.skipped))
        missing = set()
        dependency_errors = 0
        for _, trace in outcome.errors:
            # Inspect only the final exception line. A dependency name mentioned
            # in an earlier stack frame must not mask the actual test failure.
            lines = str(trace).strip().splitlines()
            final_line = lines[-1].strip() if lines else ''
            match = re.fullmatch(
                r"(?:ModuleNotFoundError|ImportError): No module named ['\"]"
                r"(flask|requests|psycopg2|gunicorn)(?:\.[A-Za-z_][A-Za-z_0-9]*)?['\"]",
                final_line,
            )
            # Keep legacy mock traces supported only when the whole error is
            # exactly the dependency message, never when mixed with other text.
            if match is None:
                match = re.fullmatch(
                    r"No module named ['\"](flask|requests|psycopg2|gunicorn)['\"]",
                    final_line,
                )
            if match:
                missing.add(match.group(1))
                dependency_errors += 1
        result['missing_dependencies'] = sorted(missing)
        if outcome.wasSuccessful() and outcome.testsRun > 0 and not outcome.skipped:
            result['status'] = 'ALL_TESTS_PASSED'
        elif (missing and dependency_errors == len(outcome.errors)
              and not outcome.failures and not outcome.skipped):
            result['status'] = 'DEPENDENCY_BLOCKED'
        else:
            result['status'] = 'TESTS_FAILED_OR_SKIPPED'
    except Exception:
        result['status'] = 'TEST_DISCOVERY_FAILED'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only offline test audit')
    parser.add_argument('--report', help='Write sanitized JSON report to this path')
    args = parser.parse_args(argv)
    result = audit()
    encoded = json.dumps(result, sort_keys=True)
    print(encoded)
    if args.report:
        try:
            target = Path(args.report)
            # Avoid accidental replacement of a symlink or unrelated file.
            if target.is_symlink() or target.exists() or not target.parent.is_dir():
                return 2
            with target.open('x', encoding='utf-8') as handle:
                handle.write(encoded + '\n')
        except (OSError, ValueError):
            return 2
    return 0 if result['status'] == 'ALL_TESTS_PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
