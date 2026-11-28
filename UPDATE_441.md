# BADANG 4.41 - Bitget OI 관측 기록 모듈

추가: `badang_oi_history_441.py`와 `test_oi_history_441.py`.

- 동일 거래소·동일 심볼·관측 시점별 OI를 SQLite에 기록.
- 실제 기록된 약 15분/1시간 전 관측값이 있을 때만 OI 변화율을 계산.
- 비교 표본이 없거나 오래되면 `None`/자료 부족을 반환; 다른 거래소 자료 혼합 금지.
- API 요청은 명시적 호출 시에만 수행. **백그라운드 연속 수집 아님**.
- 기존 앱의 신호 점수 및 UI에 아직 연결하지 않음. 자동매매 기능 없음.
- SQLite 저장 위치는 호출자가 제공하며 Render 기본 파일 시스템은 재시작 시 유실 가능. 영구 DB 설정과 배포 검증이 필요.
- Bitget 실시간 네트워크 호출은 이 환경에서 검증하지 않음. API 응답 형식은 실환경 확인 필요.

검증: `python -m unittest test_oi_history_441 test_source_gate_440 test_signal_audit_439 test_quality_438 test_integration_437 test_final_release -q`

**기존 운영 버전에 덮어쓰지 말 것.**
