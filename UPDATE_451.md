# BADANG Trading 4.51 — 체결 표본 무결성 점검

- 최대 100건 표본 응답 크기 검증
- 마지막 체결의 조회 시점 대비 경과시간을 계산해 RECENT/STALE/EMPTY로 구분
- 거래 ID가 없는 표본은 UNVERIFIABLE_IDS로 표시해 중복 검증의 한계를 명시
- 심층 화면에 신선도와 ID 검증 상태 표시
- 최근 REST 표본은 연속 CVD가 아니며 매매 점수에 반영하지 않음

주의: Bitget 실제 API/Render/Flask 통합 테스트 미검증. 배포 금지.
