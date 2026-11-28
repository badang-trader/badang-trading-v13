# BADANG Trading 5.14 — bounded test output

The offline test audit now discards test stdout/stderr and runner text without buffering it in memory. This reduces accidental exposure and memory exhaustion from noisy tests. Only sanitized aggregate JSON is printed. No changes to trade execution, exchange calls, or deployment.

Run `python -m unittest -q test_audit_bounded_output_514 test_audit_output_513 test_test_audit_508 test_test_audit_509 test_test_audit_510` and `python badang_test_audit_508.py`. Full test success still requires Flask in the environment. GitHub Actions and live Render/Bitget/PostgreSQL remain unverified.
