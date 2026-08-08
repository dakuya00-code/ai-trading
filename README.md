# ai-trading

AI 기반 자동매매 템플릿입니다. 현재 버전은 **모의(PAPER) 중심**의 최소 실행 가능한 구조를 제공합니다.

## 제공 기능

- FastAPI 기반 API 서버
- 탭 기반 전문형 모니터링 대시보드
- 실시간 차트
- 주문·체결 로그 테이블
- **보유현황 / 평가손익** 탭
- SQLite 영구 저장소
- WebSocket 실시간 갱신
- KIS 실연동용 수집기
- 자동 새로 고침 / 필터 / 알림
- 신호 분석 `/predict`
- 주문 계획 `/plan`
- 간단한 백테스트 `/backtest`
- 시세 수집 `/market/{symbol}`
- 포트폴리오 조회 `/portfolio`
- 실계좌 포트폴리오 조회 `/portfolio/live`
- 서버 상태 `/status`
- Docker / docker compose 배포

## 빠른 시작

```bash
docker compose up --build
```

기본 외부 포트는 **8010**입니다.

- 웹 UI: `http://localhost:8010/`
- 헬스체크: `http://localhost:8010/health`

## KIS 실연동

실제 KIS 시세를 사용하려면 **YAML이 아니라 환경변수(.env 또는 shell env)** 로 설정하세요.

```bash
KIS_ENABLE_LIVE=1
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
KIS_ACCOUNT_NO=63767556-01
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCESS_TOKEN=...
KIS_USER_AGENT=HermesTest/1.0
```

## 보유현황 입력

실제 계좌 연동 전에는 보유종목을 아래 두 방식으로 넣을 수 있습니다.

1. 웹 UI의 **보유현황** 탭에서 저장/수정
2. `AI_TRADING_PORTFOLIO_JSON` 환경변수 또는 `AI_TRADING_PORTFOLIO_PATH` 파일

예시:

```bash
AI_TRADING_PORTFOLIO_JSON='[
  {"symbol":"005930.KS","name":"삼성전자","quantity":10,"avg_price":72000},
  {"symbol":"000660.KS","name":"SK하이닉스","quantity":5,"avg_price":140000}
]'
```

## 데이터 저장

- 주문/체결/수집/예측 이벤트는 `AI_TRADING_DB_PATH` 에 저장됩니다.
- 포트폴리오는 `AI_TRADING_PORTFOLIO_PATH` 에 저장됩니다.
- Docker 기본값은 각각 `/app/data/ai-trading.db`, `/app/data/portfolio.json` 이며, `./data` 볼륨에 영구 저장됩니다.

## API

- `GET /`
- `GET /status`
- `GET /ready`
- `GET /version`
- `GET /collector/status`
- `GET /portfolio`
- `GET /portfolio/local`
- `GET /portfolio/live`
- `POST /portfolio/positions`
- `DELETE /portfolio/positions/{symbol}`
- `POST /portfolio/refresh`
- `GET /events`
- `GET /ws/events`
- `GET /market/{symbol}`
- `GET /health`
- `POST /predict`
- `POST /plan`
- `POST /backtest`

## 사용 예시

### 1) 웹 UI
브라우저에서 `http://localhost:8010/` 에 접속하면,
- 개요
- 차트
- 주문·체결 로그
- 보유현황
- KIS 수집기
- 설정
을 탭으로 볼 수 있습니다.

### 2) 실데이터 불러오기
웹 UI의 `실데이터 불러오기` 버튼을 누르면 `/market/{symbol}` 응답을 입력 폼에 반영합니다.

### 3) 포트폴리오 조회
```bash
curl -s http://localhost:8010/portfolio
```

### 4) 예측 API
```bash
curl -s http://localhost:8010/predict   -H 'Content-Type: application/json'   -d '{"symbol":"005930.KS","price":72000,"moving_average_short":71500,"moving_average_long":70000,"rsi":45,"sentiment":0.4}'
```

### 5) 주문 계획 API
```bash
curl -s http://localhost:8010/plan   -H 'Content-Type: application/json'   -d '{"symbol":"005930.KS","price":72000,"moving_average_short":71500,"moving_average_long":70000,"rsi":45,"sentiment":0.4}'
```

### 6) 백테스트 API
```bash
curl -s http://localhost:8010/backtest   -H 'Content-Type: application/json'   -d '{"initial_cash":10000000,"snapshots":[{"symbol":"005930.KS","price":72000,"moving_average_short":71500,"moving_average_long":70000,"rsi":45,"sentiment":0.4}]}'
```

## 주의

- 실계좌 적용 전에는 모의 환경에서 먼저 검증하세요.
- 실 API 키, OTP, 비밀번호는 저장소에 커밋하지 마세요.
