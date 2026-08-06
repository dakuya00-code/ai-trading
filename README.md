# ai-trading

프로젝트 개요

이 리포지토리는 AI 기반 자동매매(한국 주식/ETF/선물) 템플릿입니다. 실제 거래에 사용하기 전에 반드시 모의(PAPER) 환경에서 충분히 테스트하세요.

중요 경고

- 절대 실 API 키, 비밀번호, OTP 등을 코드나 커밋에 포함하지 마세요. .env.example만 커밋합니다.
- 실계좌 전환 전에는 최소 3개월 이상 모의 운용을 권장합니다.

빠른 시작 (모의 먼저)

1. .env.example을 복사하여 .env 파일을 생성하고 필요한 값을 채우세요 (실제 키는 절대 커밋하지 마세요).
2. docker-compose를 사용하여 서비스를 띄웁니다: docker-compose up --build
3. model_api가 올라오면 /predict 엔드포인트로 예측을 테스트합니다.

파일 및 구조 설명

- collector/: KIS Open API 연동 모듈
- models/: 피처/학습/추론 서비스
- agent/: 실시간 루프 및 주문 흐름
- executor/: 주문 래퍼
- risk/: 리스크 관리
- backtest/: 백테스터
- configs/: 운영 파라미터
- docs/: 사용법 및 보안 주의사항

더 자세한 실행/테스트 지침은 docs/usage.md를 확인하세요.
