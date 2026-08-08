from __future__ import annotations

from fastapi import FastAPI

from app.engine import analyze_snapshot, plan_trade, run_backtest
from app.models import BacktestRequest, BacktestResult, MarketSnapshot, PredictionResponse, TradePlan

app = FastAPI(title="ai-trading", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "model_api"}


@app.post("/predict", response_model=PredictionResponse)
def predict(snapshot: MarketSnapshot) -> PredictionResponse:
    return analyze_snapshot(snapshot)


@app.post("/plan", response_model=TradePlan)
def plan(snapshot: MarketSnapshot) -> TradePlan:
    return plan_trade(snapshot)


@app.post("/backtest", response_model=BacktestResult)
def backtest(request: BacktestRequest) -> BacktestResult:
    return run_backtest(request)
