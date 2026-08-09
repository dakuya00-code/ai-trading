from __future__ import annotations

import asyncio
import json
import base64
import binascii
import os
import secrets
from pathlib import Path
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.dashboard import dashboard_html
from app.engine import analyze_snapshot, plan_trade, run_backtest
from app.strategy_state import StrategyState, StrategyStateStore, get_strategy_store, load_strategy_state, save_strategy_state
from app.events import RealtimeHub, SQLiteEventStore, TradingEventService
from app.models import (
    BacktestRequest,
    BacktestResult,
    ExecutionResponse,
    HistoricalBacktestRequest,
    MarketSnapshot,
    PortfolioPositionRequest,
    PortfolioPositionResponse,
    PortfolioSummaryResponse,
    PortfolioUpsertResponse,
    PredictionResponse,
    TradePlan,
)
from app.portfolio import PortfolioPosition, PortfolioStore, summary_from_live_holdings
from backtest.historical import historical_snapshots
from executor.broker import KISBroker, execute_trade_plan
from collector.kis import KISLiveCollector, build_collector_from_env

DB_PATH = os.getenv('AI_TRADING_DB_PATH', 'data/ai-trading.db')
PORTFOLIO_PATH = os.getenv('AI_TRADING_PORTFOLIO_PATH', 'data/portfolio.json')
WATCHDOG_STATE_PATH = Path(os.getenv('AI_TRADING_WATCHDOG_STATE', 'data/watchdog_state.json'))
KIS_ACCOUNT_NO = os.getenv('KIS_ACCOUNT_NO', '').strip() or None
BASIC_AUTH_USER = os.getenv('AI_TRADING_BASIC_AUTH_USER', 'admin').strip() or 'admin'
BASIC_AUTH_PASSWORD = os.getenv('AI_TRADING_BASIC_AUTH_PASSWORD', '').strip()
BASIC_AUTH_ENABLED = bool(BASIC_AUTH_PASSWORD)
BASIC_AUTH_REALM = 'ai-trading'
PUBLIC_PATHS = {'/health', '/ready', '/version', '/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc'}

app = FastAPI(title='ai-trading', version='0.7.0')
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
app.state.strategy_store = StrategyStateStore(os.getenv('AI_TRADING_STRATEGY_PATH', 'data/strategy_state.json'))
app.state.strategy_state = app.state.strategy_store.load()
app.state.broker = KISBroker(account_no=KIS_ACCOUNT_NO)
app.state.live_portfolio_cache = {'summary': None, 'fetched_at': 0.0}
app.state.events.record(kind='system', level='info', message='서비스 시작', source='boot')


def _auth_challenge() -> PlainTextResponse:
    return PlainTextResponse(
        'Authentication required',
        status_code=401,
        headers={'WWW-Authenticate': f'Basic realm="{BASIC_AUTH_REALM}"'},
    )


def _is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith('/static')


def _check_basic_auth(header_value: str) -> bool:
    if not BASIC_AUTH_ENABLED:
        return True
    if not header_value.startswith('Basic '):
        return False
    try:
        decoded = base64.b64decode(header_value[6:], validate=True).decode('utf-8')
    except (binascii.Error, UnicodeDecodeError):
        return False
    username, sep, password = decoded.partition(':')
    if not sep:
        return False
    return secrets.compare_digest(username, BASIC_AUTH_USER) and secrets.compare_digest(password, BASIC_AUTH_PASSWORD)


@app.middleware('http')
async def basic_auth_middleware(request, call_next):
    if not BASIC_AUTH_ENABLED or _is_public_path(request.url.path):
        return await call_next(request)
    if not _check_basic_auth(request.headers.get('authorization', '')):
        return _auth_challenge()
    return await call_next(request)


@app.on_event('startup')
async def startup_event() -> None:
    app.state.hub.set_loop(asyncio.get_running_loop())


@app.on_event('shutdown')
async def shutdown_event() -> None:
    app.state.store.close()


def _record_event(**kwargs: Any):
    return app.state.events.record(**kwargs)


def _live_portfolio_available() -> bool:
    return bool(KIS_ACCOUNT_NO and isinstance(app.state.collector, KISLiveCollector) and app.state.collector.status.configured)


def _live_portfolio_view(force_refresh: bool = False, ttl_seconds: float = 10.0) -> PortfolioSummaryResponse:
    cache = getattr(app.state, 'live_portfolio_cache', {'summary': None, 'fetched_at': 0.0})
    now = monotonic()
    cached = cache.get('summary')
    if not force_refresh and cached is not None and (now - float(cache.get('fetched_at', 0.0))) < ttl_seconds:
        return cached
    try:
        live = app.state.collector.fetch_holdings(KIS_ACCOUNT_NO)
        summary = summary_from_live_holdings(live)
        response = PortfolioSummaryResponse.model_validate(summary.to_dict())
        app.state.live_portfolio_cache = {'summary': response, 'fetched_at': now}
        return response
    except Exception as exc:
        app.state.collector.status.last_error = str(exc)
        if cached is not None:
            return cached
        fallback = app.state.portfolio.snapshot_local()
        fallback.source = 'local-fallback'
        response = PortfolioSummaryResponse.model_validate(fallback.to_dict())
        return response


def _portfolio_view(source: str = 'auto', force_refresh: bool = False) -> PortfolioSummaryResponse:
    if source == 'live' or (source == 'auto' and _live_portfolio_available()):
        return _live_portfolio_view(force_refresh=force_refresh)
    summary = app.state.portfolio.snapshot_local()
    return PortfolioSummaryResponse.model_validate(summary.to_dict())


def _load_watchdog_market_regime() -> dict[str, Any] | None:
    if not WATCHDOG_STATE_PATH.exists():
        return None
    try:
        payload = json.loads(WATCHDOG_STATE_PATH.read_text(encoding='utf-8'))
    except Exception:
        return None
    regime = payload.get('market_regime') if isinstance(payload, dict) else None
    return regime if isinstance(regime, dict) else None


@app.get('/', response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse(dashboard_html())


@app.get('/status')
def status() -> dict[str, Any]:
    uptime_seconds = int(monotonic() - app.state.started_at)
    hours, rem = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    collector_status = app.state.collector.status.to_dict()
    portfolio = app.state.portfolio.snapshot_local()
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
        'portfolio_source': portfolio.source,
        'portfolio_live_enabled': _live_portfolio_available(),
        'strategy_profile': app.state.strategy_state.strategy_profile,
        'position_multiplier': app.state.strategy_state.position_multiplier,
        'market_regime': _load_watchdog_market_regime(),
        'db_path': str(app.state.store.path),
        'portfolio_path': str(app.state.portfolio.path),
        'account_no_configured': bool(KIS_ACCOUNT_NO),
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
def portfolio(source: str = Query(default='auto', pattern='^(auto|live|local)$')) -> PortfolioSummaryResponse:
    return _portfolio_view(source=source)


@app.get('/portfolio/local', response_model=PortfolioSummaryResponse)
def local_portfolio() -> PortfolioSummaryResponse:
    summary = app.state.portfolio.snapshot_local()
    return PortfolioSummaryResponse.model_validate(summary.to_dict())


@app.get('/portfolio/live', response_model=PortfolioSummaryResponse)
def live_portfolio() -> PortfolioSummaryResponse:
    if not _live_portfolio_available():
        raise HTTPException(status_code=400, detail='KIS 계좌 실연동이 설정되지 않았습니다.')
    return _portfolio_view(source='live')


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
    summary = _portfolio_view(force_refresh=True)
    _record_event(
        kind='portfolio',
        level='info',
        message=f'포트폴리오 새로고침 {summary.positions_count}종목',
        source='api',
        meta={'market_value': summary.total_market_value, 'pnl': summary.unrealized_pnl, 'source': summary.source},
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
    app.state.strategy_state = app.state.strategy_store.load()
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


@app.post('/backtest/historical', response_model=BacktestResult)
def backtest_historical(request: HistoricalBacktestRequest) -> BacktestResult:
    snapshots = historical_snapshots(request.symbol, period=request.period)
    result = run_backtest(BacktestRequest(initial_cash=request.initial_cash, snapshots=snapshots))
    app.state.last_backtest_return = f'{result.return_pct}%'
    _record_event(
        kind='fill',
        level='info',
        message=f'실과거 백테스트 {request.symbol}',
        symbol=request.symbol,
        return_pct=result.return_pct,
        source='historical-backtest',
        meta={'bars': len(snapshots), 'period': request.period},
    )
    return result


@app.post('/execute', response_model=ExecutionResponse)
def execute_trade(plan: TradePlan) -> ExecutionResponse:
    result = execute_trade_plan(plan, broker=app.state.broker)
    _record_event(
        kind='order',
        level='info',
        message=f'{plan.symbol} 실행 {result.status}',
        symbol=plan.symbol,
        quantity=plan.quantity,
        price=plan.entry_price,
        signal=plan.signal,
        source='broker',
        meta=result.to_dict(),
    )
    return ExecutionResponse.model_validate(result.to_dict())


@app.get('/strategy/state')
def strategy_state() -> dict[str, Any]:
    app.state.strategy_state = app.state.strategy_store.load()
    return app.state.strategy_state.to_dict()


@app.post('/strategy/reset')
def reset_strategy_state() -> dict[str, Any]:
    app.state.strategy_state = app.state.strategy_store.save(StrategyState())
    return app.state.strategy_state.to_dict()
