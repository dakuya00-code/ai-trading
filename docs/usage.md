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
- `KIS_ACCOUNT_NO` 는 실계좌 보유종목 조회용 계좌번호입니다.
- `KIS_USER_AGENT` 는 KIS 토큰/잔고 호출용 User-Agent입니다.
- `AI_TRADING_DB_PATH` 는 SQLite 이벤트 DB 경로입니다.
- `AI_TRADING_PORTFOLIO_PATH` 는 보유종목 JSON 파일 경로입니다.
- `AI_TRADING_PORTFOLIO_JSON` 로 다종목 포트폴리오를 주입할 수 있습니다.
- `./data` 디렉토리는 Docker에서 영구 저장소로 마운트됩니다.

## 화면 구성

- 개요
- 차트
- 주문·체결 로그
- 보유현황
- KIS 수집기
- 설정

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
