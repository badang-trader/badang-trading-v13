# 4.94 — Empty collection guard

An empty result list previously satisfied `all([])` and could be marked as a successful collection cycle when the runner was invoked without an explicit expected-symbol set. Empty cycles now fail closed and are recorded as failed audit runs.

Offline tests: `python -m unittest -v test_worker_empty_results_494`

This change does not establish live Bitget coverage, PostgreSQL connectivity, CVD validity, or trading readiness.
