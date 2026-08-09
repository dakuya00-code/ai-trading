from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from app.models import MarketSnapshot, TradePlan
from app.strategy_state import StrategyState


@dataclass(slots=True)
class HedgeTarget:
    hedge_symbol: str
    target_value: float
    hedge_ratio: float
    trigger_reasons: list[str]
    primary_symbols: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            'hedge_symbol': self.hedge_symbol,
            'target_value': self.target_value,
            'hedge_ratio': self.hedge_ratio,
            'trigger_reasons': self.trigger_reasons,
            'primary_symbols': self.primary_symbols,
        }


def _default_hedge_symbol() -> str:
    return os.getenv('AI_TRADING_DEFAULT_HEDGE_SYMBOL', '114800.KS').strip()


def _default_hedge_ratio() -> float:
    try:
        return float(os.getenv('AI_TRADING_HEDGE_RATIO', '0.50'))
    except Exception:
        return 0.5


def _default_hedge_trigger_pct(state: StrategyState) -> float:
    if state.strategy_profile == 'aggressive':
        return float(os.getenv('AI_TRADING_HEDGE_TRIGGER_PCT', '0.015'))
    return float(os.getenv('AI_TRADING_HEDGE_TRIGGER_PCT', '0.03'))


def load_hedge_map() -> dict[str, str]:
    raw = os.getenv('AI_TRADING_HEDGE_MAP', '').strip()
    default_symbol = _default_hedge_symbol()
    if not raw:
        return {'*': default_symbol} if default_symbol else {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            out: dict[str, str] = {}
            for key, value in parsed.items():
                if isinstance(value, str):
                    out[str(key).strip()] = value.strip()
                elif isinstance(value, dict):
                    sym = str(value.get('symbol') or value.get('hedge_symbol') or '').strip()
                    if sym:
                        out[str(key).strip()] = sym
            return out
    except Exception:
        pass
    out: dict[str, str] = {}
    for chunk in raw.split(','):
        parts = [part.strip() for part in chunk.split(':') if part.strip()]
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    if not out and default_symbol:
        out['*'] = default_symbol
    return out


def resolve_hedge_symbol(primary_symbol: str, hedge_map: dict[str, str]) -> str | None:
    return hedge_map.get(primary_symbol) or hedge_map.get('*')


def should_open_hedge(snapshot: MarketSnapshot, avg_price: float, state: StrategyState) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    trigger_pct = _default_hedge_trigger_pct(state)
    drawdown_pct = ((snapshot.price - avg_price) / avg_price) if avg_price else 0.0
    if avg_price and drawdown_pct <= -trigger_pct:
        reasons.append(f'drawdown={drawdown_pct:.3%}')
    trend_strength = getattr(snapshot, 'trend_strength', 0.0) or 0.0
    if trend_strength < 0 and snapshot.price < snapshot.moving_average_long:
        reasons.append(f'trend={trend_strength:.4f}')
    if snapshot.rsi is not None and snapshot.rsi >= 70:
        reasons.append(f'rsi={snapshot.rsi:.1f}')
    return (len(reasons) > 0), reasons


def desired_hedge_value(snapshot: MarketSnapshot, avg_price: float, quantity: int, state: StrategyState) -> tuple[float, list[str]]:
    open_hedge, reasons = should_open_hedge(snapshot, avg_price, state)
    if not open_hedge:
        return 0.0, reasons
    hedge_ratio = _default_hedge_ratio()
    market_value = max(0.0, quantity * snapshot.price)
    return market_value * hedge_ratio, reasons


def build_hedge_plan(*, hedge_symbol: str, target_value: float, hedge_snapshot: MarketSnapshot, reasons: list[str]) -> TradePlan:
    quantity = max(1, int(target_value // max(hedge_snapshot.price, 1e-9)))
    return TradePlan(
        symbol=hedge_symbol,
        signal='buy',
        quantity=quantity,
        entry_price=hedge_snapshot.price,
        stop_loss=round(hedge_snapshot.price * 0.97, 2),
        take_profit=round(hedge_snapshot.price * 1.06, 2),
        confidence=0.99,
        rationale=['hedge overlay'] + reasons,
    )
