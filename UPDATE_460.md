# BADANG Trading 4.60 — 수집 간격 설정 통합

- 워커와 API의 수집 간격 검증을 `badang_trade_config_460.py`로 일원화.
- 환경변수 `BADANG_TRADE_POLL_SECONDS` 기본값 60초, 허용 15~3600초 정수.
- 저장된 표본 품질 판단은 실제 설정값을 사용하며 API에 `expected_poll_ms` 및 설정 출처 표시.
- UI에 품질 상태와 판정 기준 표시.
- 수집 시각 공백만으로 재시작 복구 성공 또는 연속 체결 커버리지를 주장하지 않음.
- `restart_recovery_verified`와 `gap_cause_verified`는 명시적으로 false.
- Bitget/PostgreSQL/Render 실연동 미검증, CVD/매매 점수 사용 금지.
