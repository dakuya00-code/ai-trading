from __future__ import annotations

from app.engine import run_backtest
from app.models import BacktestRequest, BacktestResult, MarketSnapshot


def sample_backtest(symbol: str = "005930.KS") -> BacktestResult:
    request = BacktestRequest(
        initial_cash=10_000_000,
        snapshots=[
            MarketSnapshot(symbol=symbol, price=70000, moving_average_short=71000, moving_average_long=69000, rsi=45, sentiment=0.3),
            MarketSnapshot(symbol=symbol, price=68000, moving_average_short=67500, moving_average_long=68500, rsi=75, sentiment=-0.2),
            MarketSnapshot(symbol=symbol, price=71000, moving_average_short=70500, moving_average_long=70000, rsi=55, sentiment=0.1),
        ],
    )
    return run_backtest(request)
