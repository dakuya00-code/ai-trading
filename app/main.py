from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.dashboard import dashboard_html
from app.engine import analyze_snapshot, plan_trade, run_backtest
from app.events import RealtimeHub, SQLiteEventStore, TradingEventService
from app.models import (
    BacktestRequest,
    BacktestResult,
    MarketSnapshot,
    PortfolioPositionRequest,
    PortfolioPositionResponse,
    PortfolioSummaryResponse,
    PortfolioUpsertResponse,
    PredictionResponse,
    TradePlan,
)
from app.portfolio import PortfolioPosition, PortfolioStore
from collector.kis import build_collector_from_env

DB_PATH = os.getenv('AI_TRADING_DB_PATH', 'data/ai-trading.db')
PORTFOLIO_PATH = os.getenv('AI_TRADING_PORTFOLIO_PATH', 'data/portfolio.json')

app = FastAPI(title='ai-trading', version='0.6.0')
app.state.started_at = monotonic()
app.state.started_at_iso = datetime.now(timezone.utc).isoformat()
app.state.last_backtest_return = None
app.state.last_signal = None
app.state.last_quantity = None
app.state.latest_price = None
app.state.store = SQLiteEventStore(DB_PATH)
app.state.hub = RealtimeHub()
app.state.events = TradingEventService(app.state.store, app.state.hub)
app.state.collector = build_collector_from_env()
app.state.portfolio = PortfolioStore(PORTFOLIO_PATH)
app.state.events.record(kind='system', level='info', message='서비스 시작', source='boot')


@app.on_event('startup')
async def startup_event() -> None:
    app.state.hub.set_loop(asyncio.get_running_loop())


@app.on_event('shutdown')
async def shutdown_event() -> None:
    app.state.store.close()


def _record_event(**kwargs: Any):
    return app.state.events.record(**kwargs)


def _portfolio_view() -> PortfolioSummaryResponse:
    summary = app.state.portfolio.snapshot(app.state.collector)
    return PortfolioSummaryResponse.model_validate(summary.to_dict())


@app.get('/', response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse(dashboard_html())


@app.get('/status')
def status() -> dict[str, Any]:
    uptime_seconds = int(monotonic() - app.state.started_at)
    hours, rem = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    collector_status = app.state.collector.status.to_dict()
    portfolio = app.state.portfolio.snapshot(app.state.collector)
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
        'portfolio_positions': portfolio.positions_count,
        'portfolio_value': portfolio.total_market_value,
        'portfolio_pnl': portfolio.unrealized_pnl,
        'db_path': str(app.state.store.path),
        'portfolio_path': str(app.state.portfolio.path),
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


@app.websocket('/ws/events')
async def ws_events(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = app.state.hub.subscribe()
    try:
        for event in app.state.events.list(limit=50):
            await websocket.send_json({'type': 'snapshot', 'event': event})
        while True:
            event = await queue.get()
            await websocket.send_json({'type': 'event', 'event': event})
    except WebSocketDisconnect:
        pass
    finally:
        app.state.hub.unsubscribe(queue)


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


@app.get('/portfolio', response_model=PortfolioSummaryResponse)
def portfolio() -> PortfolioSummaryResponse:
    return _portfolio_view()


@app.post('/portfolio/positions', response_model=PortfolioUpsertResponse)
def upsert_portfolio_position(payload: PortfolioPositionRequest) -> PortfolioUpsertResponse:
    position = app.state.portfolio.upsert(
        PortfolioPosition(
            symbol=payload.symbol,
            name=payload.name,
            quantity=payload.quantity,
            avg_price=payload.avg_price,
            sector=payload.sector,
            memo=payload.memo,
        )
    )
    snapshot = app.state.collector.fetch_snapshot(position.symbol)
    row = app.state.portfolio._row_for(position, snapshot)
    _record_event(
        kind='portfolio',
        level='info',
        message=f'{position.symbol} 보유종목 저장',
        symbol=position.symbol,
        price=snapshot.price,
        quantity=position.quantity,
        source='api',
        meta={'avg_price': position.avg_price},
    )
    return PortfolioUpsertResponse(ok=True, position=PortfolioPositionResponse.model_validate(row.to_dict()))


@app.delete('/portfolio/positions/{symbol}')
def delete_portfolio_position(symbol: str) -> dict[str, Any]:
    removed = app.state.portfolio.remove(symbol)
    if removed:
        _record_event(kind='portfolio', level='info', message=f'{symbol} 보유종목 삭제', symbol=symbol, source='api')
    return {'ok': removed, 'symbol': symbol}


@app.post('/portfolio/refresh', response_model=PortfolioSummaryResponse)
def refresh_portfolio() -> PortfolioSummaryResponse:
    summary = _portfolio_view()
    _record_event(
        kind='portfolio',
        level='info',
        message=f'포트폴리오 새로고침 {summary.positions_count}종목',
        source='api',
        meta={'market_value': summary.total_market_value, 'pnl': summary.unrealized_pnl},
    )
    return summary


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
