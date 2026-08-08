from __future__ import annotations

from app.models import BacktestRequest, BacktestResult, MarketSnapshot, PredictionResponse, TradePlan
from app.risk import RiskPolicy
from app.strategy import predict_signal


RISK_POLICY = RiskPolicy()


def analyze_snapshot(snapshot: MarketSnapshot) -> PredictionResponse:
    return predict_signal(snapshot)


def plan_trade(snapshot: MarketSnapshot) -> TradePlan:
    prediction = analyze_snapshot(snapshot)
    return RISK_POLICY.build_trade_plan(snapshot, prediction)


def run_backtest(request: BacktestRequest) -> BacktestResult:
    if not request.snapshots:
        return BacktestResult(
            initial_cash=request.initial_cash,
            final_cash=request.initial_cash,
            trades=0,
            wins=0,
            losses=0,
            return_pct=0.0,
            max_drawdown_pct=0.0,
            notes=["백테스트 입력이 비어 있어 결과가 없습니다."],
        )

    cash = request.initial_cash
    peak = request.initial_cash
    equity = request.initial_cash
    trades = wins = losses = 0
    notes: list[str] = []

    for snapshot in request.snapshots:
        plan = plan_trade(snapshot)
        if plan.signal == "hold" or plan.quantity <= 0:
            notes.append(f"{snapshot.symbol}: hold")
            continue

        trades += 1
        exposure = plan.quantity * snapshot.price
        cash -= exposure * 0.01
        pnl = exposure * (0.02 if plan.signal == "buy" else -0.02)
        cash += pnl
        equity = cash
        peak = max(peak, equity)
        if pnl >= 0:
            wins += 1
        else:
            losses += 1
        notes.append(f"{snapshot.symbol}: {plan.signal} {plan.quantity}주")

    final_cash = round(cash, 2)
    return_pct = round(((final_cash - request.initial_cash) / request.initial_cash) * 100, 3)
    max_drawdown_pct = round(max(0.0, ((peak - equity) / peak) * 100), 3) if peak else 0.0

    return BacktestResult(
        initial_cash=request.initial_cash,
        final_cash=final_cash,
        trades=trades,
        wins=wins,
        losses=losses,
        return_pct=return_pct,
        max_drawdown_pct=max_drawdown_pct,
        notes=notes,
    )
