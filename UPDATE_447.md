# BADANG Trading 4.47 — 테스트 정합성 정리

기준: 4.46 ZIP 전체 프로젝트.

## 실제 변경
- `app.py`: 단타 선택 화면을 실제 서버 분석 프레임(15분, 30분, 1시간)에 맞춰 수정. 기존의 잘못된 5분 표시 제거.
- `test_release_static.py`: 실제 구현에 존재하지 않는 오래된 문구 상수 검사 대신, WAIT 방어 로직과 잘못된 매매계획 거부 코드가 존재하는지 검사하도록 변경.
- 기존 OI, CVD, 매매 점수 로직은 이번 작업에서 변경하지 않음.

## 실행 검증
- `python -m unittest discover -p 'test*.py' -q`: 56개 중 55개 통과, 1개 import 오류.
- 남은 오류: `test_oi_api_442`가 Flask를 import할 수 없음 (`ModuleNotFoundError: No module named 'flask'`). 테스트 환경에 Flask가 설치되어 있지 않음. API 기능의 합격을 뜻하지 않음.
- Bitget 실시간, PostgreSQL, Render 배포 미검증.

## 배포 상태
검토용. 실거래 환경 교체 금지. Flask 의존성을 설치한 격리 테스트 환경에서 전체 테스트 및 실제 서비스 통합 검증 필요.
