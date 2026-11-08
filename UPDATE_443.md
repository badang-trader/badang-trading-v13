# BADANG Trading 4.43 — OI 영구 저장 준비

- `DATABASE_URL` 설정 시 PostgreSQL에 Bitget OI 기록을 저장합니다. 없으면 기존 임시 SQLite를 사용합니다.
- `/api/oi-history-442?symbol=BTCUSDT` GET: OI 기록 조회. POST: OI 관측값 저장. POST는 `X-Badang-Collector-Token` 헤더가 `BADANG_OI_COLLECTOR_TOKEN` 환경변수와 일치할 때만 허용합니다.
- 자동 주기 수집은 **미구현**입니다. 실제 연속 수집은 별도 외부 스케줄러가 주기적으로 POST를 호출해야 합니다. 스케줄러 연결 전에는 `continuous_collection=false`입니다.
- Render PostgreSQL DB 및 환경변수 설정과 실제 Bitget API 연동은 아직 검증되지 않았습니다.
- CVD 연속 수집, 거래 점수 통합, 매매 신호 성과 검증도 미완료입니다.
- GitHub/Render에 아직 교체 배포하지 마세요.
- 비밀 토큰은 코드나 GitHub에 커밋하지 마세요.
