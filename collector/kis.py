from __future__ import annotations

import json
import os
import statistics
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.models import MarketSnapshot


def _is_stock_symbol(symbol: str) -> str:
    raw = symbol.split('.')[0].strip()
    return raw.zfill(6) if raw.isdigit() and len(raw) < 6 else raw


def _market_div(symbol: str) -> str:
    if symbol.endswith('.KS'):
        return 'J'
    if symbol.endswith('.KQ'):
        return 'Q'
    return os.getenv('KIS_MARKET_DIV', 'J')


def _moving_average(values: list[float], window: int) -> float:
    if not values:
        raise ValueError('값이 비어 있습니다.')
    subset = values[-min(len(values), window):]
    return round(sum(subset) / len(subset), 2)


def _simple_rsi(values: list[float], window: int = 14) -> float | None:
    if len(values) < 2:
        return None
    gains = []
    losses = []
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


@dataclass(slots=True)
class CollectorStatus:
    mode: str
    configured: bool
    base_url: str | None
    last_symbol: str | None
    last_price: float | None
    last_updated_at: str | None
    last_error: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            'mode': self.mode,
            'configured': self.configured,
            'base_url': self.base_url,
            'last_symbol': self.last_symbol,
            'last_price': self.last_price,
            'last_updated_at': self.last_updated_at,
            'last_error': self.last_error,
            'notes': self.notes,
        }


class MockKISCollector:
    name = 'mock'

    def __init__(self) -> None:
        self.status = CollectorStatus(
            mode='mock',
            configured=True,
            base_url=None,
            last_symbol=None,
            last_price=None,
            last_updated_at=None,
            notes=['모의 수집기']
        )

    def fetch_snapshot(self, symbol: str) -> MarketSnapshot:
        base = 100000 if symbol.endswith('.KS') else 100
        self.status.last_symbol = symbol
        self.status.last_price = float(base)
        self.status.last_updated_at = datetime.now(timezone.utc).isoformat()
        return MarketSnapshot(
            symbol=symbol,
            price=float(base),
            moving_average_short=round(base * 1.01, 2),
            moving_average_long=round(base * 0.99, 2),
            rsi=52,
            sentiment=0.1,
            volume=1_000_000,
        )


class KISLiveCollector:
    name = 'kis-live'

    def __init__(self, *, base_url: str, app_key: str, app_secret: str, access_token: str | None = None) -> None:
        self.base_url = base_url.rstrip('/')
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token
        self._history: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=120))
        self.status = CollectorStatus(
            mode='kis-live',
            configured=bool(base_url and app_key and app_secret),
            base_url=self.base_url,
            last_symbol=None,
            last_price=None,
            last_updated_at=None,
            notes=['KIS 실시간 시세 수집기']
        )

    def _token(self) -> str:
        if self.access_token:
            return self.access_token
        payload = json.dumps({
            'grant_type': 'client_credentials',
            'appkey': self.app_key,
            'appsecret': self.app_secret,
        }).encode('utf-8')
        req = urllib.request.Request(
            f'{self.base_url}/oauth2/tokenP',
            data=payload,
            method='POST',
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode('utf-8'))
        token = data.get('access_token') or data.get('accessToken')
        if not token:
            raise RuntimeError('KIS 토큰 응답에 access_token이 없습니다.')
        self.access_token = token
        return token

    def _fetch_price(self, symbol: str) -> tuple[float, float | None, dict[str, Any]]:
        token = self._token()
        iscd = _is_stock_symbol(symbol)
        params = urllib.parse.urlencode({
            'fid_cond_mrkt_div_code': _market_div(symbol),
            'fid_input_iscd': iscd,
        })
        url = f'{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price?{params}'
        req = urllib.request.Request(
            url,
            headers={
                'Authorization': f'Bearer {token}',
                'appkey': self.app_key,
                'appsecret': self.app_secret,
                'tr_id': os.getenv('KIS_QUOTE_TR_ID', 'FHKST01010100'),
                'custtype': 'P',
            },
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            payload = json.loads(res.read().decode('utf-8'))
        output = payload.get('output') or {}
        price_raw = output.get('stck_prpr') or output.get('last') or output.get('price')
        if price_raw is None:
            raise RuntimeError(f'KIS 가격 응답에 현재가가 없습니다: {payload}')
        volume_raw = output.get('acml_vol') or output.get('volume')
        price = float(str(price_raw).replace(',', ''))
        volume = float(str(volume_raw).replace(',', '')) if volume_raw not in (None, '') else None
        return price, volume, payload

    def fetch_snapshot(self, symbol: str) -> MarketSnapshot:
        price, volume, payload = self._fetch_price(symbol)
        history = self._history[symbol]
        history.append(price)
        prices = list(history)
        short_ma = _moving_average(prices, 5)
        long_ma = _moving_average(prices, 20)
        rsi = _simple_rsi(prices, 14)
        self.status.last_symbol = symbol
        self.status.last_price = price
        self.status.last_updated_at = datetime.now(timezone.utc).isoformat()
        self.status.last_error = None
        self.status.notes = ['KIS 실연동 시세 수집 성공']
        return MarketSnapshot(
            symbol=symbol,
            price=price,
            moving_average_short=short_ma,
            moving_average_long=long_ma,
            rsi=rsi,
            sentiment=0.0,
            volume=volume,
        )


def build_collector_from_env() -> MockKISCollector | KISLiveCollector:
    base_url = os.getenv('KIS_BASE_URL', 'https://openapivts.koreainvestment.com:29443')
    app_key = os.getenv('KIS_APP_KEY', '').strip()
    app_secret = os.getenv('KIS_APP_SECRET', '').strip()
    access_token = os.getenv('KIS_ACCESS_TOKEN', '').strip() or None
    if os.getenv('KIS_ENABLE_LIVE', '0') == '1' and app_key and app_secret:
        return KISLiveCollector(base_url=base_url, app_key=app_key, app_secret=app_secret, access_token=access_token)
    return MockKISCollector()
