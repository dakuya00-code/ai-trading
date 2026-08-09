from __future__ import annotations

from dataclasses import dataclass
from math import floor

from app.models import MarketSnapshot, PredictionResponse, TradePlan
from app.strategy_state import StrategyState, load_strategy_state


@dataclass(slots=True)
class RiskPolicy:
    max_position_value: float = 1_000_000
    min_confidence: float = 0.35
    stop_loss_pct: float = 0.03
    take_profit_pct: float = 0.06

    @classmethod
    def from_state(cls, state: StrategyState | None = None) -> 'RiskPolicy':
        state = state or load_strategy_state()
        return cls(
            max_position_value=state.max_position_value,
            min_confidence=state.min_confidence,
            stop_loss_pct=state.stop_loss_pct,
            take_profit_pct=state.take_profit_pct,
        )

    def quantity_for(self, snapshot: MarketSnapshot, confidence: float) -> int:
        if confidence < self.min_confidence:
            return 0
        budget = self.max_position_value * min(confidence, 1.0)
        shares = floor(budget / snapshot.price)
        return max(0, shares)

    def build_trade_plan(self, snapshot: MarketSnapshot, prediction: PredictionResponse) -> TradePlan:
        quantity = self.quantity_for(snapshot, prediction.confidence)
        if prediction.signal == "hold":
            quantity = 0

        stop_loss = None
        take_profit = None
        if prediction.signal == "buy" and quantity > 0:
            stop_loss = round(snapshot.price * (1 - self.stop_loss_pct), 2)
            take_profit = round(snapshot.price * (1 + self.take_profit_pct), 2)
        elif prediction.signal == "sell" and quantity > 0:
            stop_loss = round(snapshot.price * (1 + self.stop_loss_pct), 2)
            take_profit = round(snapshot.price * (1 - self.take_profit_pct), 2)

        rationale = list(prediction.rationale)
        if quantity == 0:
            rationale.append("리스크 정책에 따라 주문 수량이 0으로 제한되었습니다.")
        else:
            rationale.append(f"리스크 정책이 {quantity}주를 허용했습니다.")

        return TradePlan(
            symbol=snapshot.symbol,
            signal=prediction.signal,
            quantity=quantity,
            entry_price=snapshot.price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=prediction.confidence,
            rationale=rationale,
        )
