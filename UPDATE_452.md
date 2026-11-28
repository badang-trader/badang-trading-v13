# BADANG Trading 4.52 — REST 체결 표본 중첩 감사

추가: `badang_trade_overlap_452.py` 및 `test_trade_overlap_452.py`.
연속된 두 Bitget 최근 체결 표본에서 ID 중첩, ID 누락, 시간 역행, 중첩 없음 등을 판별한다.
**주의:** 중첩이 있어도 전체 시장 체결의 누락이 없음을 보장하지 않는다. CVD 또는 매매 신호를 생성하지 않는다.
현재 기능은 독립 감사 모듈이며 자동 수집기·화면·매매 점수에는 연결되지 않았다.
실제 Bitget/Render/PostgreSQL 연동 테스트는 하지 않았다.
