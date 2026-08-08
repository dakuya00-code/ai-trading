from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.dashboard import dashboard_html
from app.engine import analyze_snapshot, plan_trade, run_backtest
from app.models import BacktestRequest, BacktestResult, MarketSnapshot, PredictionResponse, TradePlan

app = FastAPI(title='ai-trading', version='0.3.0')
app.state.started_at = monotonic()
app.state.started_at_iso = datetime.now(timezone.utc).isoformat()
app.state.last_backtest_return = None


@app.get('/', response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse(dashboard_html())


@app.get('/status')
def status() -> dict[str, str | None]:
    uptime_seconds = int(monotonic() - app.state.started_at)
    hours, rem = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return {
        'health': 'ok',
        'service': 'ai-trading',
        'version': app.version,
        'started_at': app.state.started_at_iso,
        'uptime': f'{hours:02d}:{minutes:02d}:{seconds:02d}',
        'last_backtest_return': app.state.last_backtest_return,
    }


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'model_api'}


@app.post('/predict', response_model=PredictionResponse)
def predict(snapshot: MarketSnapshot) -> PredictionResponse:
    return analyze_snapshot(snapshot)


@app.post('/plan', response_model=TradePlan)
def plan(snapshot: MarketSnapshot) -> TradePlan:
    return plan_trade(snapshot)


@app.post('/backtest', response_model=BacktestResult)
def backtest(request: BacktestRequest) -> BacktestResult:
    result = run_backtest(request)
    app.state.last_backtest_return = f'{result.return_pct}%'
    return result
