# 4.55: One-shot REST trade sample collection job

- `badang_trade_job_455.py` fetches per-symbol Bitget recent-fill samples and stores them through the 4.54 PostgreSQL module.
- It can be called by an external scheduler (`python badang_trade_job_455.py`). It is **not** an always-running service.
- Per-symbol failure isolation, non-secret error summaries, input validation, and explicit `coverage_confirmed=False` / `is_cvd=False` are included.
- No automatic scheduler was deployed; no real Bitget or PostgreSQL integration was verified. A bounded REST endpoint does not establish gap-free continuous CVD. Do not use these samples as trading-score inputs.
- Tests: `python -m unittest -q test_trade_job_455.py`.
