# BADANG Trading 5.13 — offline audit output isolation

The offline audit now suppresses incidental stdout and stderr emitted by test discovery and test execution. The CLI emits only the deliberately sanitized JSON summary; this avoids leaking accidental diagnostic output into CI logs. Exception traces remain excluded from the JSON report. This is a log-hygiene measure, **not** proof that other workflow steps cannot print sensitive data.

Tests: `python -m unittest -q test_audit_output_513 test_ci_report_512`; full suite: `python badang_test_audit_508.py`. No deployment or trading execution.
