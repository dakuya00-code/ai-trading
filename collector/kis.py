from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.models import MarketSnapshot


def _default_headers() -> dict[str, str]:
    return {
        'Content-Type': 'application/json',
        'Accept': 'text/plain',
        'charset': 'UTF-8',
        'User-Agent': os.getenv('KIS_USER_AGENT', 'Mozilla/5.0'),
    }


def _balance_tr_id(base_url: str) -> str:
    if os.getenv('KIS_BALANCE_TR_ID'):
        return os.getenv('KIS_BALANCE_TR_ID', '')
    return 'TTTC8434R' if 'openapi.koreainvestment.com' in base_url else 'VTTC8434R'


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ''):
        return default
    try:
        return float(str(value).replace(',', '').strip())
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value in (None, ''):
        return default
    try:
        return int(float(str(value).replace(',', '').strip()))
    except Exception:
        return default


def _extract_available_cash(summary: dict[str, Any]) -> tuple[float, str | None]:
    """Best-effort extraction of usable cash from KIS balance summary."""
    if not isinstance(summary, dict):
        return 0.0, None
    candidates = [
        'ord_psbl_cash',
        'ord_psbl_amt',
        'prvs_rcdl_excc_amt',
        'nxdy_excc_amt',
        'dnca_tot_amt',
        'cma_evlu_amt',
        'cash',
        'available_cash',
        'cashable_amount',
    ]
    for key in candidates:
        value = summary.get(key)
        if value in (None, ''):
            continue
        try:
            amount = float(str(value).replace(',', '').strip())
        except Exception:
            continue
        if amount >= 0:
            return amount, key
    return 0.0, None


def _account_parts(account_no: str) -> tuple[str, str]:
    raw = account_no.strip().replace(' ', '')
    if '-' in raw:
        cano, prdt = raw.split('-', 1)
    else:
        cano, prdt = raw, os.getenv('KIS_ACCOUNT_PRDT_CD', '01')
    return cano, prdt


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
            headers=_default_headers(),
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=15) as res:
                    data = json.loads(res.read().decode('utf-8'))
                token = data.get('access_token') or data.get('accessToken')
                if not token:
                    raise RuntimeError('KIS 토큰 응답에 access_token이 없습니다.')
                self.access_token = token
                return token
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {403, 429, 500, 502, 503, 504}:
                    raise
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                body = exc.read().decode('utf-8', 'ignore')
                raise RuntimeError(f'KIS token HTTP {exc.code}: {body[:500]}') from exc
        if last_error:
            raise last_error
        raise RuntimeError('KIS token failed without response')

    def _auth_headers(self, tr_id: str) -> dict[str, str]:
        token = self._token()
        return {
            'Authorization': f'Bearer {token}',
            'appkey': self.app_key,
            'appsecret': self.app_secret,
            'tr_id': tr_id,
            'custtype': 'P',
        }

    def _get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        merged = _default_headers()
        merged.update(headers)
        req = urllib.request.Request(url, headers=merged)
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=15) as res:
                    return json.loads(res.read().decode('utf-8'))
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {403, 429, 500, 502, 503, 504}:
                    raise
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                body = exc.read().decode('utf-8', 'ignore')
                raise RuntimeError(f'KIS HTTP {exc.code}: {body[:500]}') from exc
        if last_error:
            raise last_error
        raise RuntimeError('KIS request failed without response')

    def _fetch_price(self, symbol: str) -> tuple[float, float | None, dict[str, Any]]:
        iscd = _is_stock_symbol(symbol)
        params = urllib.parse.urlencode({
            'fid_cond_mrkt_div_code': _market_div(symbol),
            'fid_input_iscd': iscd,
        })
        url = f'{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price?{params}'
        payload = self._get_json(url, self._auth_headers(os.getenv('KIS_QUOTE_TR_ID', 'FHKST01010100')))
        output = payload.get('output') or {}
        price_raw = output.get('stck_prpr') or output.get('last') or output.get('price')
        if price_raw is None:
            raise RuntimeError(f'KIS 가격 응답에 현재가가 없습니다: {payload}')
        volume_raw = output.get('acml_vol') or output.get('volume')
        price = float(str(price_raw).replace(',', ''))
        volume = float(str(volume_raw).replace(',', '')) if volume_raw not in (None, '') else None
        return price, volume, payload

    def fetch_snapshot(self, symbol: str) -> MarketSnapshot:
        price, volume, _payload = self._fetch_price(symbol)
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

    def fetch_holdings(self, account_no: str) -> dict[str, Any]:
        cano, prdt = _account_parts(account_no)
        params: dict[str, str] = {
            'CANO': cano,
            'ACNT_PRDT_CD': prdt,
            'AFHR_FLPR_YN': 'N',
            'OFL_YN': '',
            'INQR_DVSN': os.getenv('KIS_BALANCE_INQR_DVSN', '00'),
            'UNPR_DVSN': os.getenv('KIS_BALANCE_UNPR_DVSN', '01'),
            'FUND_STTL_ICLD_YN': 'N',
            'FNCG_AMT_AUTO_RDPT_YN': 'N',
            'PRCS_DVSN': '00',
        }
        ctx_fk = ''
        ctx_nk = ''
        holdings: list[dict[str, Any]] = []
        summary: dict[str, Any] = {}
        seen: set[str] = set()
        for _ in range(20):
            if ctx_fk:
                params['CTX_AREA_FK100'] = ctx_fk
                params['CTX_AREA_NK100'] = ctx_nk
            query = urllib.parse.urlencode(params)
            url = f'{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance?{query}'
            payload = self._get_json(url, self._auth_headers(_balance_tr_id(self.base_url)))
            output1 = payload.get('output1') or []
            output2 = payload.get('output2') or {}
            if isinstance(output2, list) and output2:
                output2 = output2[0]
            summary = output2 if isinstance(output2, dict) else {}
            for item in output1:
                symbol = str(item.get('pdno') or item.get('symbol') or '').strip()
                if not symbol or symbol in seen:
                    continue
                seen.add(symbol)
                holdings.append(item)
            ctx_fk = str(payload.get('ctx_area_fk100') or '').strip()
            ctx_nk = str(payload.get('ctx_area_nk100') or '').strip()
            if not ctx_fk and not ctx_nk:
                break
        available_cash, cash_source = _extract_available_cash(summary)
        return {'summary': summary, 'holdings': holdings, 'available_cash': available_cash, 'available_cash_source': cash_source}


def build_collector_from_env() -> MockKISCollector | KISLiveCollector:
    base_url = os.getenv('KIS_BASE_URL', 'https://openapivts.koreainvestment.com:29443')
    app_key = os.getenv('KIS_APP_KEY', '').strip()
    app_secret = os.getenv('KIS_APP_SECRET', '').strip()
    access_token = os.getenv('KIS_ACCESS_TOKEN', '').strip() or None
    if os.getenv('KIS_ENABLE_LIVE', '0') == '1' and app_key and app_secret:
        return KISLiveCollector(base_url=base_url, app_key=app_key, app_secret=app_secret, access_token=access_token)
    return MockKISCollector()
