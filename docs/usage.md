# Usage

## Local

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
docker compose up --build
```

기본 외부 포트는 **8010**입니다.

## 설정

- KIS 관련 비밀값은 YAML이 아니라 환경변수(.env 또는 shell env)에 넣습니다.
- `AI_TRADING_DB_PATH` 는 SQLite 이벤트 DB 경로입니다.
- `./data` 디렉토리는 Docker에서 영구 저장소로 마운트됩니다.

## 화면 구성

- 개요
- 차트
- 주문·체결 로그
- KIS 수집기
- 설정

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
