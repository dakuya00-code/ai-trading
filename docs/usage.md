# Usage

## Local

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
```

## API

- `GET /health`
- `POST /predict`
- `POST /plan`
- `POST /backtest`
