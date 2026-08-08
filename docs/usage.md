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
- `GET /market/{symbol}`
- `GET /health`
- `POST /predict`
- `POST /plan`
- `POST /backtest`
