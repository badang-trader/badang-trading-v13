# BADANG Trading 4.44 — 외부 스케줄러용 OI 수집 작업

- 추가: `badang_oi_job_444.py` (한 번 실행하고 종료하는 Bitget OI 수집 작업).
- 기본 종목 BTCUSDT, ETHUSDT. `BADANG_OI_SYMBOLS` 환경변수 또는 `--symbols BTCUSDT,ETHUSDT`로 지정 (최대 20개).
- PostgreSQL `DATABASE_URL` 필수. DB가 없으면 오류 종료하며 임시 저장소로 조용히 전환하지 않음.
- 종목별 오류를 분리하여 나머지 종목은 계속 수집. 민감한 예외 메시지는 출력하지 않음.
- Render Cron Job 등 **별도 스케줄러**에서 `python badang_oi_job_444.py`를 1~5분마다 실행하도록 구성해야 실제 연속 수집이 시작됨. 웹 서버의 백그라운드 스레드나 사용자 접속에 의존하지 않음.
- **주의:** 스케줄러, 실제 Bitget API, PostgreSQL, Render 배포는 이 환경에서 검증되지 않았음. 현재 `app.py`의 `/api/oi-history-442`는 스케줄러 상태를 직접 감지하지 못하므로 `continuous_collection=false`를 유지함. 자동 수집이 활성화되었다고 표시하지 않음.
- CVD 수집, 통합 점수 연결, 실거래 성과 검증은 미완료. GitHub/Render 기존 버전은 교체하지 말 것.
