BADANG 2.0.2 스캔 진단 패치
- 단타: 15m/30m/1H, 스윙: 1H/4H/1D
- /api/v13-scan 배치 크기 5 -> 1: Render 요청당 작업량 축소
- 화면의 요청 대기 50초 초과 시 오류 표시
- 스캔 성공은 보장되지 않음. Render Logs의 Python traceback과 API 상태 확인 필요.
- 기존 기능과 데이터 완전성 보호 로직 유지.
- GitHub 저장소 루트에 내부 파일을 올리고 배포하세요. __pycache__는 업로드하지 마세요.
