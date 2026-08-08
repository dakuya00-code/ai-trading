from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from app.dashboard import dashboard_html
from app.engine import analyze_snapshot, plan_trade, run_backtest
from app.events import EventStore
from app.models import BacktestRequest, BacktestResult, MarketSnapshot, PredictionResponse, TradePlan
from collector.kis import build_collector_from_env

app = FastAPI(title='ai-trading', version='0.4.0')
app.state.started_at = monotonic()
app.state.started_at_iso = datetime.now(timezone.utc).isoformat()
app.state.last_backtest_return = None
app.state.last_signal = None
app.state.last_quantity = None
app.state.latest_price = None
app.state.events = EventStore(maxlen=500)
app.state.collector = build_collector_from_env()
app.state.events.record(kind='system', level='info', message='서비스 시작', source='boot')


def _record_event(**kwargs: Any):
    return app.state.events.record(**kwargs)


@app.get('/', response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse(dashboard_html())


@app.get('/status')
def status() -> dict[str, Any]:
    uptime_seconds = int(monotonic() - app.state.started_at)
    hours, rem = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    collector_status = app.state.collector.status.to_dict()
    return {
        'health': 'ok',
        'service': 'ai-trading',
        'version': app.version,
        'started_at': app.state.started_at_iso,
        'uptime': f'{hours:02d}:{minutes:02d}:{seconds:02d}',
        'last_backtest_return': app.state.last_backtest_return,
        'last_signal': app.state.last_signal,
        'last_quantity': app.state.last_quantity,
        'latest_price': app.state.latest_price,
        'event_count': app.state.events.count(),
        'collector_mode': collector_status['mode'],
        'collector_configured': collector_status['configured'],
    }


@app.get('/ready')
def ready() -> dict[str, str]:
    return {'status': 'ready', 'service': 'ai-trading'}


@app.get('/version')
def version() -> dict[str, str]:
    return {
        'version': app.version,
        'started_at': app.state.started_at_iso,
        'collector_mode': app.state.collector.status.mode,
    }


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'model_api'}


@app.get('/events')
def events(
    limit: int = Query(default=50, ge=1, le=200),
    kind: str | None = None,
    level: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    return app.state.events.list(limit=limit, kind=kind, level=level, query=query)


@app.get('/collector/status')
def collector_status() -> dict[str, Any]:
    return app.state.collector.status.to_dict()


@app.get('/market/{symbol}')
def market_snapshot(symbol: str) -> MarketSnapshot:
    snapshot = app.state.collector.fetch_snapshot(symbol)
    app.state.latest_price = snapshot.price
    _record_event(
        kind='collector',
        level='info',
        message=f'{symbol} 시세 수집',
        symbol=symbol,
        price=snapshot.price,
        source=app.state.collector.status.mode,
        meta={'source': 'collector'},
    )
    return snapshot


@app.post('/predict', response_model=PredictionResponse)
def predict(snapshot: MarketSnapshot) -> PredictionResponse:
    result = analyze_snapshot(snapshot)
    app.state.last_signal = result.signal
    app.state.latest_price = snapshot.price
    _record_event(
        kind='predict',
        level='info',
        message=f'{snapshot.symbol} 예측 {result.signal}',
        symbol=snapshot.symbol,
        price=snapshot.price,
        signal=result.signal,
        confidence=result.confidence,
        source='api',
    )
    return result


@app.post('/plan', response_model=TradePlan)
def plan(snapshot: MarketSnapshot) -> TradePlan:
    result = plan_trade(snapshot)
    app.state.last_quantity = result.quantity
    app.state.last_signal = result.signal
    _record_event(
        kind='order',
        level='info',
        message=f'{snapshot.symbol} 주문 계획 {result.signal}',
        symbol=snapshot.symbol,
        price=snapshot.price,
        signal=result.signal,
        confidence=result.confidence,
        quantity=result.quantity,
        source='api',
    )
    return result


@app.post('/backtest', response_model=BacktestResult)
def backtest(request: BacktestRequest) -> BacktestResult:
    result = run_backtest(request)
    app.state.last_backtest_return = f'{result.return_pct}%'
    _record_event(
        kind='fill',
        level='info',
        message=f'백테스트 {result.trades}건',
        return_pct=result.return_pct,
        source='backtest',
        meta={'wins': result.wins, 'losses': result.losses},
    )
    return result
