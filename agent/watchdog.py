from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.hedge import build_hedge_plan, detect_market_regime, market_overlay_target
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
            return {'rules': [], 'hedges': {}, 'last_run_at': None, 'market_regime': None}
        try:
            payload = json.loads(self.path.read_text(encoding='utf-8'))
            payload.setdefault('hedges', {})
            payload.setdefault('market_regime', None)
            return payload
        except Exception:
            return {'rules': [], 'hedges': {}, 'last_run_at': None, 'market_regime': None}

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
    holdings_by_symbol = {str(item.get('pdno') or item.get('symbol') or '').strip(): item for item in holdings if str(item.get('pdno') or item.get('symbol') or '').strip()}
    rules = _build_rules(collector, account_no, override_symbols=override_symbols)
    strategy = load_strategy_state()

    benchmark_symbol = os.getenv('AI_TRADING_MARKET_BENCHMARK_SYMBOL', '069500.KS').strip()
    inverse_symbol = os.getenv('AI_TRADING_INVERSE_SYMBOL', os.getenv('AI_TRADING_DEFAULT_HEDGE_SYMBOL', '114800.KS')).strip()
    benchmark_snapshot = collector.fetch_snapshot(benchmark_symbol)
    regime = detect_market_regime(benchmark_snapshot, strategy)
    state.data['market_regime'] = regime.to_dict()
    state.save()

    portfolio_value = 0.0
    for item in holdings:
        qty_raw = item.get('hldg_qty') or item.get('quantity') or item.get('qty') or 0
        current_raw = item.get('prpr') or item.get('stck_prpr') or item.get('evlu_pric') or item.get('current_price') or 0
        try:
            qty = int(float(str(qty_raw).replace(',', '').strip()))
        except Exception:
            qty = 0
        try:
            current_price = float(str(current_raw).replace(',', '').strip())
        except Exception:
            current_price = 0.0
        portfolio_value += max(0.0, qty * current_price)

    for rule in rules:
        state.mark_rule(rule)
        snapshot = collector.fetch_snapshot(rule.symbol)
        triggered = None
        if snapshot.price <= rule.stop_loss:
            triggered = 'stop_loss'
        elif snapshot.price >= rule.take_profit:
            triggered = 'take_profit'
        if not _market_is_open():
            reports.append({'symbol': rule.symbol, 'name': rule.name, 'price': snapshot.price, 'triggered': 'market_closed', 'stop_loss': rule.stop_loss, 'take_profit': rule.take_profit})
            continue
        if triggered:
            plan = TradePlan(symbol=rule.symbol, signal='sell', quantity=rule.quantity, entry_price=snapshot.price, stop_loss=None, take_profit=None, confidence=1.0, rationale=[f'watchdog {triggered}'])
            execution = execute_trade_plan(plan, broker=broker)
            state.mark_triggered(rule.symbol)
            reports.append({'symbol': rule.symbol, 'name': rule.name, 'price': snapshot.price, 'triggered': triggered, 'stop_loss': rule.stop_loss, 'take_profit': rule.take_profit, 'execution': execution.to_dict()})
        else:
            reports.append({'symbol': rule.symbol, 'name': rule.name, 'price': snapshot.price, 'triggered': None, 'stop_loss': rule.stop_loss, 'take_profit': rule.take_profit})

    target_inverse_value = market_overlay_target(portfolio_value, regime)
    inverse_snapshot = collector.fetch_snapshot(inverse_symbol)
    inverse_item = holdings_by_symbol.get(inverse_symbol) or {}
    inverse_qty_raw = inverse_item.get('hldg_qty') or inverse_item.get('quantity') or inverse_item.get('qty') or 0
    try:
        inverse_current_qty = int(float(str(inverse_qty_raw).replace(',', '').strip()))
    except Exception:
        inverse_current_qty = 0
    inverse_target_qty = max(0, int(target_inverse_value // max(inverse_snapshot.price, 1e-9)))

    if not _market_is_open():
        reports.append({'symbol': inverse_symbol, 'name': '인버스 헤지', 'price': inverse_snapshot.price, 'triggered': 'market_closed', 'market_regime': regime.to_dict(), 'target_inverse_value': target_inverse_value, 'target_inverse_qty': inverse_target_qty, 'current_inverse_qty': inverse_current_qty})
    else:
        if regime.regime == 'bullish' and inverse_current_qty > 0:
            close_plan = TradePlan(symbol=inverse_symbol, signal='sell', quantity=inverse_current_qty, entry_price=inverse_snapshot.price, stop_loss=None, take_profit=None, confidence=0.99, rationale=['시장 강세라 인버스 청산'])
            execution = execute_trade_plan(close_plan, broker=broker)
            state.mark_hedge_closed(inverse_symbol)
            reports.append({'symbol': inverse_symbol, 'name': '인버스 헤지', 'price': inverse_snapshot.price, 'triggered': 'inverse_close_bullish', 'market_regime': regime.to_dict(), 'execution': execution.to_dict()})
        elif regime.regime in {'bearish', 'neutral'}:
            if inverse_target_qty > inverse_current_qty:
                buy_qty = inverse_target_qty - inverse_current_qty
                hedge_plan = build_hedge_plan(hedge_symbol=inverse_symbol, target_value=buy_qty * inverse_snapshot.price, hedge_snapshot=inverse_snapshot, reasons=[('시장 약세 인버스 확대' if regime.regime == 'bearish' else '중립 인버스 소액 유지')] + regime.trigger_reasons)
                hedge_plan.quantity = buy_qty
                execution = execute_trade_plan(hedge_plan, broker=broker)
                state.mark_hedge_open(inverse_symbol, {'market_regime': regime.to_dict(), 'target_inverse_value': target_inverse_value, 'target_inverse_qty': inverse_target_qty, 'execution': execution.to_dict()})
                reports.append({'symbol': inverse_symbol, 'name': '인버스 헤지', 'price': inverse_snapshot.price, 'triggered': 'inverse_buy', 'market_regime': regime.to_dict(), 'execution': execution.to_dict()})
            elif inverse_target_qty < inverse_current_qty:
                sell_qty = inverse_current_qty - inverse_target_qty
                close_plan = TradePlan(symbol=inverse_symbol, signal='sell', quantity=sell_qty, entry_price=inverse_snapshot.price, stop_loss=None, take_profit=None, confidence=0.99, rationale=['인버스 비중 축소'])
                execution = execute_trade_plan(close_plan, broker=broker)
                reports.append({'symbol': inverse_symbol, 'name': '인버스 헤지', 'price': inverse_snapshot.price, 'triggered': 'inverse_trim', 'market_regime': regime.to_dict(), 'execution': execution.to_dict()})
            else:
                reports.append({'symbol': inverse_symbol, 'name': '인버스 헤지', 'price': inverse_snapshot.price, 'triggered': None, 'market_regime': regime.to_dict(), 'target_inverse_value': target_inverse_value, 'target_inverse_qty': inverse_target_qty, 'current_inverse_qty': inverse_current_qty})

    if os.getenv('AI_TRADING_ENABLE_NAME_HEDGE_MAP', '0') == '1':
        from app.hedge import load_hedge_map, resolve_hedge_symbol
        hedge_map = load_hedge_map()
        for rule in rules:
            hedge_symbol = resolve_hedge_symbol(rule.symbol, hedge_map, rule.name)
            if hedge_symbol and hedge_symbol != rule.symbol:
                reports.append({'symbol': rule.symbol, 'name': rule.name, 'mapped_hedge_symbol': hedge_symbol, 'note': 'name hedge map enabled'})

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
