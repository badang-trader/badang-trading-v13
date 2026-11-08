# BADANG Trading 4.78 — Predeployment gate

Run `python badang_predeploy_478.py` in the target Render environment.

1. Validate configuration offline (4.77).
2. Only when configuration is valid, run read-only database checks (4.76).
3. Output fixed, secret-safe JSON and exit 0 only if both pass.

No migration, order placement, Bitget API request or live CVD validation.
Passing is NOT approval for live trading. Never paste DATABASE_URL or passwords into chat.

Tests: `python -m unittest -q test_predeploy_478 test_deploy_check_477 test_readiness_476`.
