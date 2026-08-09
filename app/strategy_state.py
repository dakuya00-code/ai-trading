from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.models import BacktestResult


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(slots=True)
class StrategyState:
    buy_threshold: float = 0.35
    sell_threshold: float = -0.35
    min_confidence: float = 0.35
    stop_loss_pct: float = 0.03
    take_profit_pct: float = 0.06
    max_position_value: float = 1_000_000.0
    trend_weight: float = 0.5
    price_weight: float = 0.25
    rsi_weight: float = 0.2
    sentiment_weight: float = 0.3
    trade_samples: int = 0
    last_return_pct: float | None = None
    last_win_rate: float | None = None
    last_drawdown_pct: float | None = None
    last_update_reason: str = 'initial'
    notebook_sources: list[str] = field(default_factory=lambda: [
        '시장 국면·리스크온오프',
        '워치리스트·촉매·실적',
        '국내·미국 차트 규칙',
        '리스크 규칙·사이징·무효화',
        '주문·조회·실행 플로우',
        '트레이드 복기·실수·패턴',
    ])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'StrategyState':
        defaults = cls()
        fields = defaults.to_dict().keys()
        payload: dict[str, Any] = {}
        for key in fields:
            value = data.get(key, getattr(defaults, key))
            payload[key] = value
        return cls(**payload)

    def adapt_from_backtest(self, result: BacktestResult) -> 'StrategyState':
        win_rate = (result.wins / result.trades) if result.trades else 0.0
        self.trade_samples += max(0, result.trades)
        self.last_return_pct = result.return_pct
        self.last_win_rate = round(win_rate, 3)
        self.last_drawdown_pct = result.max_drawdown_pct
        if result.trades == 0:
            self.last_update_reason = 'no-trades'
            return self

        if result.return_pct > 0 and win_rate >= 0.55 and result.max_drawdown_pct <= 5:
            self.buy_threshold = _clamp(self.buy_threshold - 0.01, 0.20, 0.70)
            self.sell_threshold = -self.buy_threshold
            self.min_confidence = _clamp(self.min_confidence - 0.01, 0.20, 0.80)
            self.take_profit_pct = _clamp(self.take_profit_pct + 0.005, 0.03, 0.15)
            self.stop_loss_pct = _clamp(self.stop_loss_pct + 0.002, 0.02, 0.08)
            self.max_position_value = _clamp(self.max_position_value * 1.05, 100_000, 5_000_000)
            self.last_update_reason = 'expanded-after-positive-backtest'
        elif result.return_pct < 0 or win_rate < 0.45 or result.max_drawdown_pct > 8:
            self.buy_threshold = _clamp(self.buy_threshold + 0.02, 0.20, 0.80)
            self.sell_threshold = -self.buy_threshold
            self.min_confidence = _clamp(self.min_confidence + 0.02, 0.20, 0.90)
            self.take_profit_pct = _clamp(self.take_profit_pct - 0.005, 0.03, 0.12)
            self.stop_loss_pct = _clamp(self.stop_loss_pct - 0.003, 0.015, 0.06)
            self.max_position_value = _clamp(self.max_position_value * 0.90, 50_000, 3_000_000)
            self.last_update_reason = 'tightened-after-negative-backtest'
        else:
            self.last_update_reason = 'stable-no-change'
        return self


class StrategyStateStore:
    def __init__(self, path: str | os.PathLike[str] = 'data/strategy_state.json') -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> StrategyState:
        if not self.path.exists():
            return StrategyState()
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            return StrategyState()
        if not isinstance(raw, dict):
            return StrategyState()
        return StrategyState.from_dict(raw)

    def save(self, state: StrategyState) -> StrategyState:
        self.path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        return state

    def update_from_backtest(self, result: BacktestResult) -> StrategyState:
        state = self.load()
        state.adapt_from_backtest(result)
        return self.save(state)


_DEFAULT_STORE: StrategyStateStore | None = None


def get_strategy_store() -> StrategyStateStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = StrategyStateStore(os.getenv('AI_TRADING_STRATEGY_PATH', 'data/strategy_state.json'))
    return _DEFAULT_STORE


def load_strategy_state() -> StrategyState:
    return get_strategy_store().load()


def save_strategy_state(state: StrategyState) -> StrategyState:
    return get_strategy_store().save(state)


def learn_from_backtest(result: BacktestResult) -> StrategyState:
    return get_strategy_store().update_from_backtest(result)
