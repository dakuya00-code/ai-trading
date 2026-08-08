# ai-trading

AI 기반 자동매매 템플릿입니다. 현재 버전은 **모의(PAPER) 중심**의 최소 실행 가능한 구조를 제공합니다.

## 제공 기능

- FastAPI 기반 API 서버
- 신호 분석 `/predict`
- 주문 계획 `/plan`
- 간단한 백테스트 `/backtest`
- Docker / docker compose 배포
- GitHub Actions 빌드 워크플로우

## 빠른 시작

```bash
cp .env.example .env  # 선택 사항
docker compose up --build
```

## API

- `GET /health`
- `POST /predict`
- `POST /plan`
- `POST /backtest`

## 주의

- 실계좌 적용 전에는 모의 환경에서 먼저 검증하세요.
- 실 API 키, OTP, 비밀번호는 저장소에 커밋하지 마세요.
