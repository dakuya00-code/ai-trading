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

## API

- `GET /`
- `GET /status`
- `GET /health`
- `POST /predict`
- `POST /plan`
- `POST /backtest`
