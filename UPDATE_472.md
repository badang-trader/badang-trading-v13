# 4.72 — Collection status anomaly propagation

Fix: PostgreSQL `status()` returns a minimal CLOCK_OR_RECORD_ANOMALY object without `latest_age_ms`. `collection_status()` previously raised KeyError instead of returning a safe diagnostic. It now propagates the anomaly and returns a fail-closed quality state. Added five integration regression tests. This does not establish complete CVD coverage or validate live Render/PostgreSQL connectivity.
