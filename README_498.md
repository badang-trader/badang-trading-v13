# BADANG Trading 4.98 — 저장 건수 일치성 점검

읽기 전용: `python badang_storage_consistency_498.py`

`DATABASE_URL` 및 PostgreSQL 접근이 가능한 실행 환경에서만 실제 점검이 가능합니다. 마지막 200건의 저장된 JSON 배열 길이와 `sample_count`를 비교합니다. 성공 결과는 `SAMPLE_COUNTS_MATCH`이며, 전체 체결 수집 보장·CVD 검증·자동 주문 허용을 의미하지 않습니다. 실제 Render/Bitget/PostgreSQL 연결은 별도 검증이 필요합니다. 원본 배포에는 자동 반영되지 않습니다.
