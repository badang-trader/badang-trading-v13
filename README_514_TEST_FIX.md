# BADANG 5.14 test collection repair

`test_oi_api_442.py` now marks the Flask integration module as skipped if Flask is unavailable, instead of aborting collection of unrelated offline tests. This does **not** validate the OI API or fix missing Flask.

For a complete run, install `requirements.txt` into an isolated environment, then run `python -m pytest -q`. Flask integration tests must execute and pass (not skip) in CI before live deployment.

No trading logic, API endpoints, exchange access, credentials or deployment settings were changed.
