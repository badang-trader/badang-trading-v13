# 4.71 — PostgreSQL 수집 상태 조회 무결성

- `snapshot_count`는 전체 누적 건수가 아닌 최신 최대 1,000건의 조회 결과임을 명시.
- 조회 상한에 도달한 경우 `history_truncated_or_at_limit`을 표시. 실제 초과 여부는 알 수 없음.
- 수집 시각 중복, 역순, 미래 시각, 비정상 시각은 오류 상태로 처리.
- 체결 표본의 완전성, 연속 CVD, 매매 점수 사용 여부는 계속 false.
- 실제 PostgreSQL·Bitget·Render 연결은 이 로컬 테스트에서 검증하지 않음.
