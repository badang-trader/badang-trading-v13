# 4.59 — REST 체결 표본 수집 품질 진단

- `/api/trade-collection-458`의 응답에 `quality_status`, `quality_message`, `expected_poll_ms`를 추가했습니다.
- 상태: NO_RECORDS, STALE, INSUFFICIENT_HISTORY, GAP_DETECTED, CLOCK_ANOMALY, SNAPSHOTS_REGULAR.
- 기본 수집 간격 60초, 허용 간격 2배 기준. 실제 worker의 BADANG_TRADE_POLL_SECONDS가 다르면 해당 값과 일치하도록 후속 설정 연동이 필요합니다.
- 저장된 최근 최대 1000회 스냅샷만 검사합니다. 정상 상태라도 전체 체결 연속성은 검증되지 않습니다.
- CVD/매매 점수 반영은 계속 금지합니다.
- 테스트: 신규 8개 포함 전체 117개 실행 중 116개 통과, 1개 Flask 미설치로 import 오류.
- 실제 Bitget, PostgreSQL, Render 통합 검증은 미실시. 배포 금지 검토본.
