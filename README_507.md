# BADANG Trading 5.07 — Per-symbol evidence validation

The read-only operational gate now verifies actual per-symbol inspected row counts, rather than accepting only a global count and an empty missing-symbol list. Counts must be positive, within the query limit, sum to the reported total, and match configured symbols exactly. This is not evidence of full-market trade coverage or validated CVD. No order execution or database writes are added. Deployment and live integrations are not tested by this release.
