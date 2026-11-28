# BADANG Trading 4.81 — 종목별 수집 최신성 점검

기존 4.80의 전체 MAX(fetched_ms) 조회는 한 종목의 최근 기록이 다른 종목의 수집 중단을 가릴 수 있었습니다.

`python badang_symbol_freshness_481.py`는 배포 사전점검을 통과한 뒤, BADANG_TRADE_SYMBOLS의 각 종목별 최신 저장 시각을 읽기 전용으로 조회합니다. 모든 종목이 최근 기록을 보유할 때만 종료 코드 0을 반환합니다. 설정 오류, 누락/오래된 기록, 쿼리 오류는 종료 코드 1입니다.

**주의:** 최근 REST 체결 표본의 존재는 완전한 체결 커버리지, CVD, 자동 주문 안전성을 증명하지 않습니다. `trading_ready` 및 `safe_to_enable_orders`는 항상 false입니다. Render/PostgreSQL 실서버 검증은 별도 수행해야 합니다.
