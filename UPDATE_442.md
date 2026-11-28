# BADANG Trading 4.42 — OI API 연결 (검토용)

- 4.41 OI 관측 모듈을 Flask API에 연결.
- `GET /api/oi-history-442?symbol=BTCUSDT`: 저장된 OI 관측 변화 조회 (외부 API 호출 없음).
- `POST /api/oi-history-442?symbol=BTCUSDT`: 사용자 명시 요청으로 Bitget OI 1회 조회 및 로컬 SQLite 기록.
- 동일 종목 POST 최소 60초 간격 (프로세스 내 제한; 다중 인스턴스 공유 제한 아님).
- 15분/1시간 변화는 해당 시점의 과거 관측 기록이 있을 때만 계산.
- OI는 매매 점수에 반영하지 않음. CVD 미구현. 자동 수집 미구현.
- 로컬 SQLite는 Render 재배포/재시작 시 소실 가능. `BADANG_OI_DB_PATH` 경로 설정 가능하나 영구 저장 보장은 별도 설정 필요.
- 사용자 화면에 버튼 추가하지 않았음. 기존 화면 및 기존 매매 동작 유지.

## 검증
- `python -m unittest test_oi_history_441 -q`: 8개 통과.
- `python -m compileall -q .`: 통과.
- `test_oi_api_442.py`: 추가했지만 실행 환경에 Flask가 설치되어 있지 않고 패키지 설치 네트워크가 막혀 **실행 검증 불가**.
- 실제 Bitget API / Render 배포: 미검증.
- 따라서 현재 버전을 실거래용으로 배포하지 말 것.
