# ai-trading

AI 기반 자동매매 템플릿입니다. 현재 버전은 **모의(PAPER) 중심**의 최소 실행 가능한 구조를 제공합니다.

## 제공 기능

- FastAPI 기반 API 서버
- 전문형 웹 UI 대시보드
- 신호 분석 `/predict`
- 주문 계획 `/plan`
- 간단한 백테스트 `/backtest`
- 서버 상태 `/status`
- Docker / docker compose 배포
- GitHub Actions 빌드 워크플로우

## 빠른 시작

```bash
docker compose up --build
```

기본 접속 포트는 **8010**입니다.

- 웹 UI: `http://localhost:8010/`
- 헬스체크: `http://localhost:8010/health`

## API

- `GET /`
- `GET /status`
- `GET /health`
- `POST /predict`
- `POST /plan`
- `POST /backtest`

## 사용 예시

### 1) 웹 UI
브라우저에서 `http://localhost:8010/` 에 접속하면,
- 서버 상태
- 예측 결과
- 주문 계획
- 백테스트 결과
를 한 화면에서 모니터링할 수 있습니다.

### 2) 예측 API
```bash
curl -s http://localhost:8010/predict   -H 'Content-Type: application/json'   -d '{"symbol":"005930.KS","price":72000,"moving_average_short":71500,"moving_average_long":70000,"rsi":45,"sentiment":0.4}'
```

### 3) 주문 계획 API
```bash
curl -s http://localhost:8010/plan   -H 'Content-Type: application/json'   -d '{"symbol":"005930.KS","price":72000,"moving_average_short":71500,"moving_average_long":70000,"rsi":45,"sentiment":0.4}'
```

### 4) 백테스트 API
```bash
curl -s http://localhost:8010/backtest   -H 'Content-Type: application/json'   -d '{"initial_cash":10000000,"snapshots":[{"symbol":"005930.KS","price":72000,"moving_average_short":71500,"moving_average_long":70000,"rsi":45,"sentiment":0.4}]}'
```

## 주의

- 실계좌 적용 전에는 모의 환경에서 먼저 검증하세요.
- 실 API 키, OTP, 비밀번호는 저장소에 커밋하지 마세요.
