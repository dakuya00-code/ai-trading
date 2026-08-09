from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import fmean
from typing import Any

from app.models import MarketSnapshot


@dataclass(slots=True)
class HistoricalBar:
    ts: int
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None


def _rsi(values: list[float], window: int = 14) -> float:
    if len(values) < 2:
        return 50.0
    window = min(window, len(values) - 1)
    if window <= 0:
        return 50.0
    gains: list[float] = []
    losses: list[float] = []
    for prev, current in zip(values[-(window + 1):-1], values[-window:]):
        delta = current - prev
        if delta >= 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))
    if not gains and not losses:
        return 50.0
    avg_gain = sum(gains) / max(1, len(gains))
    avg_loss = sum(losses) / max(1, len(losses))
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def fetch_yahoo_daily_bars(symbol: str, period: str = '1y') -> list[HistoricalBar]:
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range={period}&interval=1d&includeAdjustedClose=true&events=div,splits'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as res:
        payload = json.loads(res.read().decode('utf-8'))
    chart = payload.get('chart') or {}
    if chart.get('error'):
        raise RuntimeError(f'Yahoo chart error: {chart["error"]}')
    results = chart.get('result') or []
    if not results:
        raise RuntimeError('Yahoo chart response is empty')
    result = results[0]
    timestamps = result.get('timestamp') or []
    quote = ((result.get('indicators') or {}).get('quote') or [{}])[0]
    opens = quote.get('open') or []
    highs = quote.get('high') or []
    lows = quote.get('low') or []
    closes = quote.get('close') or []
    volumes = quote.get('volume') or []
    bars: list[HistoricalBar] = []
    for idx, ts in enumerate(timestamps):
        close = closes[idx] if idx < len(closes) else None
        if close is None:
            continue
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
        bars.append(
            HistoricalBar(
                ts=int(ts),
                date=dt,
                open=float(opens[idx]) if idx < len(opens) and opens[idx] is not None else float(close),
                high=float(highs[idx]) if idx < len(highs) and highs[idx] is not None else float(close),
                low=float(lows[idx]) if idx < len(lows) and lows[idx] is not None else float(close),
                close=float(close),
                volume=float(volumes[idx]) if idx < len(volumes) and volumes[idx] is not None else None,
            )
        )
    if not bars:
        raise RuntimeError('No historical bars with close prices')
    return bars


def bars_to_snapshots(symbol: str, bars: list[HistoricalBar]) -> list[MarketSnapshot]:
    closes: list[float] = []
    snapshots: list[MarketSnapshot] = []
    for bar in bars:
        closes.append(bar.close)
        short_window = closes[-min(len(closes), 5):]
        long_window = closes[-min(len(closes), 20):]
        ma_short = round(fmean(short_window), 2)
        ma_long = round(fmean(long_window), 2)
        rsi = _rsi(closes, 14) if len(closes) > 1 else 50.0
        snapshots.append(
            MarketSnapshot(
                symbol=symbol,
                price=bar.close,
                moving_average_short=ma_short,
                moving_average_long=ma_long,
                rsi=rsi,
                sentiment=0.0,
                volume=bar.volume,
            )
        )
    return snapshots


def historical_snapshots(symbol: str, period: str = '1y') -> list[MarketSnapshot]:
    return bars_to_snapshots(symbol, fetch_yahoo_daily_bars(symbol, period=period))
