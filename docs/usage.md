# Usage

## Local

```bash
cp .env.example .env
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
