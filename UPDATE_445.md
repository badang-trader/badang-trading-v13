# BADANG Trading 4.45 — OI collector safety patch

Source: 4.44 archive. Existing application files preserved except the narrow API error-path change.

## Changed
- `app.py`: A failed POST `/api/oi-history-442` no longer locks the symbol out for 60 seconds. The reservation is released only when it still belongs to the failed request. Logs record exception class rather than raw exception content.
- `test_oi_retry_445.py`: regression tests for independent per-symbol collection and symbol validation.

## Important limitations
- Cron is **not deployed**. No evidence of continuous OI collection or persisted history on Render.
- The GET endpoint only reads existing OI observations; OI is not integrated into trade score.
- CVD collection and signal backtesting are not implemented.
- The existing static release tests fail on expectations that do not match the current app; these are not silently declared passed.
- No Bitget or PostgreSQL live integration test was run. Do not replace the running production deployment with this review build.

## Test environment
Python 3.13; missing Flask dependency prevents importing the Flask API test. Run `pip install -r requirements.txt` in an isolated environment before full test suite.
