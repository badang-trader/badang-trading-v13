# BADANG Trading 5.11 — reproducible offline CI

Adds `.github/workflows/offline-tests.yml`, an optional GitHub Actions workflow
that installs the exact declared dependencies and runs the entire test audit.
It has read-only repository permissions, no credentials, no DB URL, no order
execution, and no deploy step. The workflow only runs if this repository code
is committed to GitHub; packaging a ZIP does not enable CI.

The local environment cannot install Flask because package-index DNS is unavailable.
Thus the full test suite remains **blocked** locally. A future green CI run would
verify the offline tests, **not** Bitget data continuity, PostgreSQL persistence,
Render uptime, or trading readiness. Do not enable live orders based on CI alone.
