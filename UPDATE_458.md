# 4.58: 저장된 체결 표본 상태 화면
- GET /api/trade-collection-458?symbol=BTCUSDT: PostgreSQL 최근 최대 1000개 수집 시각에 대한 조회 전용 상태.
- 심층 조회 시 최근 저장 표본 수, 마지막 기록 경과시간, 최대 수집 간격을 표시.
- 3분 내 기록이 있어도 연속 수집 또는 전체 시장 체결 커버리지를 보장하지 않음.
- CVD/매매 점수/자동 주문에 사용하지 않음.
- Render PostgreSQL 연결 및 별도 worker 실제 배포는 미검증.
