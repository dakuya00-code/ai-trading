from __future__ import annotations

from dataclasses import dataclass

from app.models import MarketSnapshot


@dataclass(slots=True)
class MockKISCollector:
    name: str = "mock-kis"

    def fetch_snapshot(self, symbol: str) -> MarketSnapshot:
        base = 100000 if symbol.endswith(".KS") else 100
        return MarketSnapshot(
            symbol=symbol,
            price=base,
            moving_average_short=base * 1.01,
            moving_average_long=base * 0.99,
            rsi=52,
            sentiment=0.1,
            volume=1_000_000,
        )
