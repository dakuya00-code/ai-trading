# ai-trading

AI 기반 자동매매 템플릿입니다. 현재 버전은 **모의(PAPER) 중심**의 최소 실행 가능한 구조를 제공합니다.

## 제공 기능

- FastAPI 기반 API 서버
- 탭 기반 전문형 모니터링 대시보드
- 실시간 차트
- 주문·체결 로그 테이블
- SQLite 영구 저장소
- WebSocket 실시간 갱신
- KIS 실연동용 수집기
- 자동 새로고침 / 필터 / 알림
- 신호 분석 `/predict`
- 주문 계획 `/plan`
- 간단한 백테스트 `/backtest`
- 시세 수집 `/market/{symbol}`
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
KIS_BASE_URL=https://openapivts.koreainvestment.com:29443
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCESS_TOKEN=...
```

## 데이터 저장

- 주문/체결/수집/예측 이벤트는 `AI_TRADING_DB_PATH` 에 저장됩니다.
- Docker 기본값은 `/app/data/ai-trading.db` 이며, `./data` 볼륨에 영구 저장됩니다.

## API

- `GET /`
- `GET /status`
- `GET /ready`
- `GET /version`
- `GET /collector/status`
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
- 실시간 차트
- 주문·체결 로그
- KIS 수집기
- 설정
을 탭으로 볼 수 있습니다.

### 2) 실데이터 불러오기
웹 UI의 `실데이터 불러오기` 버튼을 누르면 `/market/{symbol}` 응답을 입력 폼에 반영합니다.

### 3) 예측 API
```bash
curl -s http://localhost:8010/predict   -H 'Content-Type: application/json'   -d '{"symbol":"005930.KS","price":72000,"moving_average_short":71500,"moving_average_long":70000,"rsi":45,"sentiment":0.4}'
```

### 4) 주문 계획 API
```bash
curl -s http://localhost:8010/plan   -H 'Content-Type: application/json'   -d '{"symbol":"005930.KS","price":72000,"moving_average_short":71500,"moving_average_long":70000,"rsi":45,"sentiment":0.4}'
```

### 5) 백테스트 API
```bash
curl -s http://localhost:8010/backtest   -H 'Content-Type: application/json'   -d '{"initial_cash":10000000,"snapshots":[{"symbol":"005930.KS","price":72000,"moving_average_short":71500,"moving_average_long":70000,"rsi":45,"sentiment":0.4}]}'
```

## 주의

- 실계좌 적용 전에는 모의 환경에서 먼저 검증하세요.
- 실 API 키, OTP, 비밀번호는 저장소에 커밋하지 마세요.
