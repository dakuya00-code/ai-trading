from __future__ import annotations

from dataclasses import asdict, dataclass

from app.engine import plan_trade
from app.strategy_state import load_strategy_state
from collector.kis import MockKISCollector
from executor.orders import to_order


@dataclass(slots=True)
class TradingLoop:
    collector: MockKISCollector

    def step(self, symbol: str) -> dict[str, object]:
        snapshot = self.collector.fetch_snapshot(symbol)
        strategy_state = load_strategy_state()
        plan = plan_trade(snapshot)
        order = to_order(plan)
        return {
            "snapshot": snapshot.model_dump(),
            "strategy_state": strategy_state.to_dict(),
            "plan": plan.model_dump(),
            "order": None if order is None else asdict(order),
        }
