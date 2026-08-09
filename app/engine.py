from __future__ import annotations

from app.models import BacktestRequest, BacktestResult, MarketSnapshot, PredictionResponse, TradePlan
from app.risk import RiskPolicy
from app.strategy import predict_signal
from app.strategy_state import learn_from_backtest, load_strategy_state


def analyze_snapshot(snapshot: MarketSnapshot) -> PredictionResponse:
    state = load_strategy_state()
    return predict_signal(snapshot, state=state)


def plan_trade(snapshot: MarketSnapshot) -> TradePlan:
    state = load_strategy_state()
    prediction = predict_signal(snapshot, state=state)
    return RiskPolicy.from_state(state).build_trade_plan(snapshot, prediction)


def _simulate_backtest(request: BacktestRequest) -> BacktestResult:
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
    equity_peak = request.initial_cash
    max_drawdown_pct = 0.0
    trades = wins = losses = 0
    notes: list[str] = []
    position_qty = 0
    entry_price = 0.0
    entry_stop = None
    entry_take = None

    for snapshot in request.snapshots:
        plan = plan_trade(snapshot)
        price = snapshot.price

        if position_qty > 0:
            exit_reason = None
            if entry_stop is not None and price <= entry_stop:
                exit_reason = 'stop_loss'
            elif entry_take is not None and price >= entry_take:
                exit_reason = 'take_profit'
            elif plan.signal == 'sell':
                exit_reason = 'signal_exit'

            if exit_reason:
                cash += position_qty * price
                pnl = (price - entry_price) * position_qty
                if pnl >= 0:
                    wins += 1
                else:
                    losses += 1
                trades += 1
                notes.append(f'{snapshot.symbol}: exit {exit_reason} @ {price:.2f} pnl={pnl:.2f}')
                position_qty = 0
                entry_price = 0.0
                entry_stop = None
                entry_take = None

        if position_qty == 0 and plan.signal == 'buy' and plan.quantity > 0:
            position_qty = plan.quantity
            entry_price = price
            entry_stop = plan.stop_loss
            entry_take = plan.take_profit
            cash -= position_qty * price
            trades += 1
            notes.append(f'{snapshot.symbol}: entry buy {position_qty} @ {price:.2f}')

        equity = cash + position_qty * price
        equity_peak = max(equity_peak, equity)
        if equity_peak > 0:
            drawdown = ((equity_peak - equity) / equity_peak) * 100
            max_drawdown_pct = max(max_drawdown_pct, drawdown)

    if position_qty > 0:
        last_price = request.snapshots[-1].price
        cash += position_qty * last_price
        pnl = (last_price - entry_price) * position_qty
        if pnl >= 0:
            wins += 1
        else:
            losses += 1
        trades += 1
        notes.append(f'{request.snapshots[-1].symbol}: forced exit @ {last_price:.2f} pnl={pnl:.2f}')

    final_cash = round(cash, 2)
    return_pct = round(((final_cash - request.initial_cash) / request.initial_cash) * 100, 3)
    result = BacktestResult(
        initial_cash=request.initial_cash,
        final_cash=final_cash,
        trades=trades,
        wins=wins,
        losses=losses,
        return_pct=return_pct,
        max_drawdown_pct=round(max_drawdown_pct, 3),
        notes=notes,
    )
    learned = learn_from_backtest(result)
    result.notes.append(
        f"학습 반영: buy_threshold={learned.buy_threshold:.2f}, min_confidence={learned.min_confidence:.2f}, stop_loss={learned.stop_loss_pct:.3f}, take_profit={learned.take_profit_pct:.3f}, max_position_value={learned.max_position_value:.0f}"
    )
    return result


def run_backtest(request: BacktestRequest) -> BacktestResult:
    return _simulate_backtest(request)
