from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

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


@dataclass(slots=True)
class MarketRegimeDecision:
    regime: Literal['bullish', 'neutral', 'bearish']
    benchmark_symbol: str
    benchmark_price: float
    target_inverse_ratio: float
    target_position_multiplier: float
    trigger_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            'regime': self.regime,
            'benchmark_symbol': self.benchmark_symbol,
            'benchmark_price': self.benchmark_price,
            'target_inverse_ratio': self.target_inverse_ratio,
            'target_position_multiplier': self.target_position_multiplier,
            'trigger_reasons': self.trigger_reasons,
        }


def _default_hedge_symbol() -> str:
    return os.getenv('AI_TRADING_DEFAULT_HEDGE_SYMBOL', '114800.KS').strip()


def _benchmark_symbol() -> str:
    return os.getenv('AI_TRADING_MARKET_BENCHMARK_SYMBOL', '069500.KS').strip()


def _inverse_symbol() -> str:
    return os.getenv('AI_TRADING_INVERSE_SYMBOL', _default_hedge_symbol()).strip()


def _default_hedge_ratio() -> float:
    try:
        return float(os.getenv('AI_TRADING_HEDGE_RATIO', '0.50'))
    except Exception:
        return 0.5


def _default_hedge_trigger_pct(state: StrategyState) -> float:
    if state.strategy_profile == 'aggressive':
        return float(os.getenv('AI_TRADING_HEDGE_TRIGGER_PCT', '0.015'))
    return float(os.getenv('AI_TRADING_HEDGE_TRIGGER_PCT', '0.03'))


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


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


def resolve_hedge_symbol(primary_symbol: str, hedge_map: dict[str, str], primary_name: str | None = None) -> str | None:
    return hedge_map.get(primary_symbol) or (primary_name and hedge_map.get(primary_name)) or hedge_map.get('*')


def detect_market_regime(benchmark_snapshot: MarketSnapshot, state: StrategyState) -> MarketRegimeDecision:
    trend_strength = getattr(benchmark_snapshot, 'trend_strength', 0.0) or 0.0
    bullish_reasons: list[str] = []
    bearish_reasons: list[str] = []

    if benchmark_snapshot.moving_average_short >= benchmark_snapshot.moving_average_long:
        bullish_reasons.append('단기 이동평균이 장기 이동평균 이상입니다')
    else:
        bearish_reasons.append('단기 이동평균이 장기 이동평균 이하입니다')

    if benchmark_snapshot.price >= benchmark_snapshot.moving_average_long:
        bullish_reasons.append('벤치마크가 장기 이동평균 위에 있습니다')
    else:
        bearish_reasons.append('벤치마크가 장기 이동평균 아래에 있습니다')

    if trend_strength > 0.01:
        bullish_reasons.append(f'추세 강도 양수({trend_strength:.4f})')
    elif trend_strength < -0.01:
        bearish_reasons.append(f'추세 강도 음수({trend_strength:.4f})')

    if benchmark_snapshot.rsi is not None:
        if benchmark_snapshot.rsi < 45:
            bearish_reasons.append(f'RSI 약세({benchmark_snapshot.rsi:.1f})')
        elif benchmark_snapshot.rsi > 70:
            bearish_reasons.append(f'RSI 과열({benchmark_snapshot.rsi:.1f})')
        else:
            bullish_reasons.append(f'RSI 중립/강세({benchmark_snapshot.rsi:.1f})')

    if len(bullish_reasons) >= 2 and len(bearish_reasons) < 2:
        regime = 'bullish'
        inverse_ratio = _float_env('AI_TRADING_BULLISH_INVERSE_RATIO', 0.0)
        position_multiplier = _float_env('AI_TRADING_BULLISH_POSITION_MULTIPLIER', 2.0 if state.strategy_profile == 'aggressive' else 1.3)
        reasons = bullish_reasons
    elif len(bearish_reasons) >= 2:
        regime = 'bearish'
        inverse_ratio = _float_env('AI_TRADING_BEARISH_INVERSE_RATIO', _default_hedge_ratio())
        position_multiplier = _float_env('AI_TRADING_BEARISH_POSITION_MULTIPLIER', 0.6 if state.strategy_profile == 'aggressive' else 0.8)
        reasons = bearish_reasons
    else:
        regime = 'neutral'
        inverse_ratio = _float_env('AI_TRADING_NEUTRAL_INVERSE_RATIO', 0.15)
        position_multiplier = _float_env('AI_TRADING_NEUTRAL_POSITION_MULTIPLIER', 1.0)
        reasons = bullish_reasons + bearish_reasons

    return MarketRegimeDecision(
        regime=regime,
        benchmark_symbol=benchmark_snapshot.symbol,
        benchmark_price=benchmark_snapshot.price,
        target_inverse_ratio=max(0.0, min(1.0, inverse_ratio)),
        target_position_multiplier=max(0.5, min(5.0, position_multiplier)),
        trigger_reasons=reasons,
    )


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


def market_overlay_target(portfolio_value: float, regime: MarketRegimeDecision) -> float:
    return max(0.0, portfolio_value * regime.target_inverse_ratio)


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
