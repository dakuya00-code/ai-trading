from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.hedge import build_hedge_plan, desired_hedge_value, load_hedge_map, resolve_hedge_symbol
from app.strategy_state import load_strategy_state
from collector.kis import KISLiveCollector, build_collector_from_env
from executor.broker import KISBroker, execute_trade_plan
from app.models import TradePlan


KST = timezone(timedelta(hours=9))
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


class WatchdogState:
    def __init__(self, path: Path = STATE_PATH) -> None:
        self.path = path
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {'rules': [], 'hedges': {}, 'last_run_at': None}
        try:
            payload = json.loads(self.path.read_text(encoding='utf-8'))
            if 'hedges' not in payload:
                payload['hedges'] = {}
            return payload
        except Exception:
            return {'rules': [], 'hedges': {}, 'last_run_at': None}

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

    def hedge_active(self, hedge_symbol: str) -> bool:
        return bool((self.data.get('hedges') or {}).get(hedge_symbol, {}).get('status') == 'open')

    def mark_hedge_open(self, hedge_symbol: str, payload: dict[str, Any]) -> None:
        hedges = self.data.setdefault('hedges', {})
        hedges[hedge_symbol] = {'status': 'open', 'opened_at': datetime.now(timezone.utc).isoformat(), **payload}
        self.save()

    def mark_hedge_closed(self, hedge_symbol: str) -> None:
        hedges = self.data.setdefault('hedges', {})
        current = hedges.get(hedge_symbol) or {}
        hedges[hedge_symbol] = {**current, 'status': 'closed', 'closed_at': datetime.now(timezone.utc).isoformat()}
        self.save()


def _market_is_open(now: datetime | None = None) -> bool:
    now = now or datetime.now(KST)
    if now.weekday() >= 5:
        return False
    market_open = dtime(9, 0)
    market_close = dtime(15, 30)
    return market_open <= now.time() <= market_close


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
    holdings_payload = collector.fetch_holdings(account_no)
    holdings = holdings_payload.get('holdings') or []
    held_symbols = {str(item.get('pdno') or item.get('symbol') or '').strip() for item in holdings if str(item.get('pdno') or item.get('symbol') or '').strip()}
    holdings_by_symbol = {str(item.get('pdno') or item.get('symbol') or '').strip(): item for item in holdings if str(item.get('pdno') or item.get('symbol') or '').strip()}
    rules = _build_rules(collector, account_no, override_symbols=override_symbols)
    hedge_map = load_hedge_map()
    strategy = load_strategy_state()
    desired_hedges: dict[str, dict[str, Any]] = {}

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

        hedge_symbol = resolve_hedge_symbol(rule.symbol, hedge_map)
        if hedge_symbol and hedge_symbol != rule.symbol:
            hedge_snapshot = collector.fetch_snapshot(hedge_symbol)
            target_value, reasons = desired_hedge_value(snapshot, rule.avg_price, rule.quantity, strategy)
            if target_value > 0:
                desired_hedges[hedge_symbol] = {
                    'target_value': desired_hedges.get(hedge_symbol, {}).get('target_value', 0.0) + target_value,
                    'primary_symbols': sorted(set(desired_hedges.get(hedge_symbol, {}).get('primary_symbols', []) + [rule.symbol])),
                    'reasons': sorted(set(desired_hedges.get(hedge_symbol, {}).get('reasons', []) + reasons)),
                    'hedge_snapshot': hedge_snapshot,
                }
            elif state.hedge_active(hedge_symbol) and hedge_symbol not in held_symbols:
                state.mark_hedge_closed(hedge_symbol)

    for hedge_symbol, payload in desired_hedges.items():
        hedge_snapshot = payload['hedge_snapshot']
        if hedge_symbol in held_symbols or state.hedge_active(hedge_symbol):
            continue
        if not _market_is_open():
            reports.append({
                'symbol': hedge_symbol,
                'name': 'hedge',
                'price': hedge_snapshot.price,
                'triggered': 'market_closed',
                'hedge_for': payload['primary_symbols'],
            })
            continue
        hedge_plan = build_hedge_plan(
            hedge_symbol=hedge_symbol,
            target_value=payload['target_value'],
            hedge_snapshot=hedge_snapshot,
            reasons=payload['reasons'],
        )
        execution = execute_trade_plan(hedge_plan, broker=broker)
        state.mark_hedge_open(hedge_symbol, {
            'primary_symbols': payload['primary_symbols'],
            'target_value': payload['target_value'],
            'reasons': payload['reasons'],
            'execution': execution.to_dict(),
        })
        reports.append({
            'symbol': hedge_symbol,
            'name': 'hedge',
            'price': hedge_snapshot.price,
            'triggered': 'hedge_open',
            'hedge_for': payload['primary_symbols'],
            'execution': execution.to_dict(),
        })

    active_hedges = dict(state.data.get('hedges') or {})
    for hedge_symbol, hedge_state in active_hedges.items():
        if hedge_symbol in desired_hedges:
            continue
        if hedge_symbol not in held_symbols:
            state.mark_hedge_closed(hedge_symbol)
            continue
        if not _market_is_open():
            continue
        hedge_item = holdings_by_symbol.get(hedge_symbol) or {}
        qty_raw = hedge_item.get('hldg_qty') or hedge_item.get('quantity') or hedge_item.get('qty') or 0
        try:
            qty = int(float(str(qty_raw).replace(',', '').strip()))
        except Exception:
            qty = 0
        if qty <= 0:
            state.mark_hedge_closed(hedge_symbol)
            continue
        close_snapshot = collector.fetch_snapshot(hedge_symbol)
        close_plan = TradePlan(
            symbol=hedge_symbol,
            signal='sell',
            quantity=qty,
            entry_price=close_snapshot.price,
            stop_loss=None,
            take_profit=None,
            confidence=0.99,
            rationale=['hedge unwind'],
        )
        execution = execute_trade_plan(close_plan, broker=broker)
        state.mark_hedge_closed(hedge_symbol)
        reports.append({
            'symbol': hedge_symbol,
            'name': 'hedge',
            'price': close_snapshot.price,
            'triggered': 'hedge_close',
            'execution': execution.to_dict(),
            'hedge_state': hedge_state,
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
    print(json.dumps({'status': 'started', 'interval': interval, 'live_orders': broker.enable_live_orders, 'account': account_no, 'profile': load_strategy_state().strategy_profile}, ensure_ascii=False), flush=True)
    while True:
        try:
            reports = _scan_once(collector, broker, account_no, state, override_symbols=override_symbols)
            print(json.dumps({'ts': datetime.now(timezone.utc).isoformat(), 'reports': reports}, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({'ts': datetime.now(timezone.utc).isoformat(), 'error': str(exc)}, ensure_ascii=False), flush=True)
        time.sleep(interval)


if __name__ == '__main__':
    main()
