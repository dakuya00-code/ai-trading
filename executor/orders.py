from __future__ import annotations

from dataclasses import dataclass

from app.models import TradePlan


@dataclass(slots=True)
class OrderInstruction:
    symbol: str
    side: str
    quantity: int
    limit_price: float | None


def to_order(plan: TradePlan) -> OrderInstruction | None:
    if plan.quantity <= 0 or plan.signal == "hold":
        return None
    side = "buy" if plan.signal == "buy" else "sell"
    return OrderInstruction(symbol=plan.symbol, side=side, quantity=plan.quantity, limit_price=plan.entry_price)
