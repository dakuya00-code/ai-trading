from __future__ import annotations

import json
import os
import time
from datetime import date
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.strategy_state import load_strategy_state
from collector.kis import KISLiveCollector, build_collector_from_env
from executor.broker import KISBroker, execute_trade_plan
from app.models import TradePlan


STATE_PATH = Path(os.getenv('AI_TRADING_WATCHDOG_STATE', 'data/watchdog_state.json'))
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class WatchRule:
    symbol: str
    quantity: int
    avg_price: float
    stop_loss: float
    take_profit: float
    name: str = ''
    triggered_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)




def _market_is_open(now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    kst = now.astimezone().astimezone() if False else None
    # Use local UTC weekday as a conservative weekend gate; on this host the goal is to suppress Sunday triggers.
    return now.weekday() < 5

class WatchdogState:
    def __init__(self, path: Path = STATE_PATH) -> None:
        self.path = path
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {'rules': [], 'last_run_at': None}
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            return {'rules': [], 'last_run_at': None}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')

    def mark_rule(self, rule: WatchRule) -> None:
        rules = [r for r in self.data.get('rules', []) if r.get('symbol') != rule.symbol]
        rules.append(rule.to_dict())
        self.data['rules'] = rules
        self.save()

    def mark_triggered(self, symbol: str) -> None:
        for rule in self.data.get('rules', []):
            if rule.get('symbol') == symbol:
                rule['triggered_at'] = datetime.now(timezone.utc).isoformat()
        self.data['last_run_at'] = datetime.now(timezone.utc).isoformat()
        self.save()


def _build_rules(collector: KISLiveCollector, account_no: str, *, override_symbols: list[str] | None = None) -> list[WatchRule]:
    holdings_payload = collector.fetch_holdings(account_no)
    holdings = holdings_payload.get('holdings') or []
    strategy = load_strategy_state()
    watch_rules: list[WatchRule] = []
    for item in holdings:
        symbol = str(item.get('pdno') or item.get('symbol') or '').strip()
        if not symbol:
            continue
        if override_symbols and symbol not in override_symbols:
            continue
        qty_raw = item.get('hldg_qty') or item.get('quantity') or item.get('qty') or 0
        avg_raw = item.get('pchs_avg_pric') or item.get('avg_price') or item.get('buy_price') or item.get('prpr') or 0
        try:
            quantity = int(float(str(qty_raw).replace(',', '').strip()))
        except Exception:
            quantity = 0
        try:
            avg_price = float(str(avg_raw).replace(',', '').strip())
        except Exception:
            avg_price = 0.0
        if quantity <= 0 or avg_price <= 0:
            continue
        stop_loss = round(avg_price * (1 - strategy.stop_loss_pct), 2)
        take_profit = round(avg_price * (1 + strategy.take_profit_pct), 2)
        watch_rules.append(WatchRule(symbol=symbol, quantity=quantity, avg_price=avg_price, stop_loss=stop_loss, take_profit=take_profit, name=str(item.get('prdt_name') or item.get('name') or symbol)))
    return watch_rules


def _scan_once(collector: KISLiveCollector, broker: KISBroker, account_no: str, state: WatchdogState, *, override_symbols: list[str] | None = None) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    rules = _build_rules(collector, account_no, override_symbols=override_symbols)
    for rule in rules:
        state.mark_rule(rule)
        snapshot = collector.fetch_snapshot(rule.symbol)
        triggered = None
        if snapshot.price <= rule.stop_loss:
            triggered = 'stop_loss'
        elif snapshot.price >= rule.take_profit:
            triggered = 'take_profit'
        if not _market_is_open():
            reports.append({
                'symbol': rule.symbol,
                'name': rule.name,
                'price': snapshot.price,
                'triggered': 'market_closed',
                'stop_loss': rule.stop_loss,
                'take_profit': rule.take_profit,
            })
            continue
        if triggered:
            plan = TradePlan(
                symbol=rule.symbol,
                signal='sell',
                quantity=rule.quantity,
                entry_price=snapshot.price,
                stop_loss=None,
                take_profit=None,
                confidence=1.0,
                rationale=[f'watchdog {triggered}'],
            )
            execution = execute_trade_plan(plan, broker=broker)
            state.mark_triggered(rule.symbol)
            reports.append({
                'symbol': rule.symbol,
                'name': rule.name,
                'price': snapshot.price,
                'triggered': triggered,
                'stop_loss': rule.stop_loss,
                'take_profit': rule.take_profit,
                'execution': execution.to_dict(),
            })
        else:
            reports.append({
                'symbol': rule.symbol,
                'name': rule.name,
                'price': snapshot.price,
                'triggered': None,
                'stop_loss': rule.stop_loss,
                'take_profit': rule.take_profit,
            })
    state.data['last_run_at'] = datetime.now(timezone.utc).isoformat()
    state.save()
    return reports


def main() -> None:
    account_no = os.getenv('KIS_ACCOUNT_NO', '').strip()
    if not account_no:
        raise SystemExit('KIS_ACCOUNT_NO is required')
    collector = build_collector_from_env()
    if not isinstance(collector, KISLiveCollector):
        raise SystemExit('KIS live collector is not configured')
    broker = KISBroker(account_no=account_no)
    interval = float(os.getenv('AI_TRADING_WATCH_INTERVAL_SECONDS', '300'))
    state = WatchdogState()
    override = [s.strip() for s in os.getenv('AI_TRADING_WATCH_SYMBOLS', '').split(',') if s.strip()]
    override_symbols = override or None
    print(json.dumps({'status': 'started', 'interval': interval, 'live_orders': broker.enable_live_orders, 'account': account_no}, ensure_ascii=False), flush=True)
    while True:
        try:
            reports = _scan_once(collector, broker, account_no, state, override_symbols=override_symbols)
            print(json.dumps({'ts': datetime.now(timezone.utc).isoformat(), 'reports': reports}, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({'ts': datetime.now(timezone.utc).isoformat(), 'error': str(exc)}, ensure_ascii=False), flush=True)
        time.sleep(interval)


if __name__ == '__main__':
    main()
