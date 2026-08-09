from __future__ import annotations

import base64
import binascii
import json
import os
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from executor.orders import OrderInstruction, to_order
from app.models import TradePlan


def _account_parts(account_no: str) -> tuple[str, str]:
    raw = account_no.strip().replace(' ', '')
    if '-' in raw:
        cano, prdt = raw.split('-', 1)
    else:
        cano, prdt = raw, os.getenv('KIS_ACCOUNT_PRDT_CD', '01')
    return cano, prdt


def _default_headers() -> dict[str, str]:
    return {
        'Content-Type': 'application/json',
        'Accept': 'text/plain',
        'charset': 'UTF-8',
        'User-Agent': os.getenv('KIS_USER_AGENT', 'Mozilla/5.0'),
    }


@dataclass(slots=True)
class OrderExecutionResult:
    symbol: str
    side: str
    quantity: int
    limit_price: float | None
    dry_run: bool
    submitted: bool
    status: str
    order_id: str | None = None
    message: str = ''
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'limit_price': self.limit_price,
            'dry_run': self.dry_run,
            'submitted': self.submitted,
            'status': self.status,
            'order_id': self.order_id,
            'message': self.message,
            'raw': self.raw,
        }


class KISBroker:
    def __init__(self, *, base_url: str | None = None, app_key: str | None = None, app_secret: str | None = None, access_token: str | None = None, account_no: str | None = None, enable_live_orders: bool | None = None) -> None:
        self.base_url = (base_url or os.getenv('KIS_BASE_URL', 'https://openapivts.koreainvestment.com:29443')).rstrip('/')
        self.app_key = app_key or os.getenv('KIS_APP_KEY', '').strip()
        self.app_secret = app_secret or os.getenv('KIS_APP_SECRET', '').strip()
        self.access_token = access_token or os.getenv('KIS_ACCESS_TOKEN', '').strip() or None
        self.account_no = account_no or os.getenv('KIS_ACCOUNT_NO', '').strip() or None
        self.enable_live_orders = bool(enable_live_orders if enable_live_orders is not None else os.getenv('AI_TRADING_ENABLE_LIVE_ORDERS', '0') == '1')

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
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.loads(res.read().decode('utf-8'))
        token = data.get('access_token') or data.get('accessToken')
        if not token:
            raise RuntimeError('KIS 토큰 응답에 access_token이 없습니다.')
        self.access_token = token
        return token

    def _hashkey(self, payload: dict[str, Any]) -> str:
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            f'{self.base_url}/uapi/hashkey',
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'appKey': self.app_key,
                'appSecret': self.app_secret,
            },
        )
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.loads(res.read().decode('utf-8'))
        hashkey = data.get('HASH') or data.get('hashkey') or data.get('hash')
        if not hashkey:
            raise RuntimeError('KIS hashkey 응답에 HASH가 없습니다.')
        return str(hashkey)

    def _auth_headers(self, tr_id: str, payload: dict[str, Any] | None = None) -> dict[str, str]:
        token = self._token()
        headers = {
            'authorization': f'Bearer {token}',
            'appkey': self.app_key,
            'appsecret': self.app_secret,
            'tr_id': tr_id,
            'custtype': 'P',
        }
        if payload is not None:
            headers['hashkey'] = self._hashkey(payload)
        return headers

    def submit(self, instruction: OrderInstruction) -> OrderExecutionResult:
        if not self.enable_live_orders:
            return OrderExecutionResult(
                symbol=instruction.symbol,
                side=instruction.side,
                quantity=instruction.quantity,
                limit_price=instruction.limit_price,
                dry_run=True,
                submitted=False,
                status='dry-run',
                message='실주문 비활성화 상태입니다.',
            )
        if not self.account_no:
            raise RuntimeError('KIS_ACCOUNT_NO가 설정되지 않았습니다.')
        cano, prdt = _account_parts(self.account_no)
        payload = {
            'CANO': cano,
            'ACNT_PRDT_CD': prdt,
            'PDNO': instruction.symbol.split('.')[0],
            'ORD_DVSN': '00',
            'ORD_QTY': str(instruction.quantity),
            'ORD_UNPR': str(int(round(instruction.limit_price or 0))),
        }
        tr_id = os.getenv('KIS_BUY_TR_ID', 'TTTC0802U') if instruction.side == 'buy' else os.getenv('KIS_SELL_TR_ID', 'TTTC0801U')
        req = urllib.request.Request(
            f'{self.base_url}/uapi/domestic-stock/v1/trading/order-cash',
            data=json.dumps(payload).encode('utf-8'),
            method='POST',
            headers=_default_headers() | self._auth_headers(tr_id, payload),
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            text = res.read().decode('utf-8')
            try:
                data = json.loads(text)
            except Exception:
                data = {'raw_text': text}
        output = data.get('output') if isinstance(data, dict) else {}
        order_id = None
        if isinstance(output, dict):
            order_id = output.get('ODNO') or output.get('odno') or output.get('order_no')
        return OrderExecutionResult(
            symbol=instruction.symbol,
            side=instruction.side,
            quantity=instruction.quantity,
            limit_price=instruction.limit_price,
            dry_run=False,
            submitted=True,
            status='submitted',
            order_id=str(order_id) if order_id is not None else None,
            message='KIS 주문이 제출되었습니다.',
            raw=data if isinstance(data, dict) else {'raw_text': text},
        )


def execute_trade_plan(plan: TradePlan, broker: KISBroker | None = None) -> OrderExecutionResult:
    instruction = to_order(plan)
    if instruction is None:
        return OrderExecutionResult(
            symbol=plan.symbol,
            side='hold',
            quantity=0,
            limit_price=None,
            dry_run=True,
            submitted=False,
            status='skipped',
            message='주문 수량이 0이거나 hold 신호입니다.',
        )
    broker = broker or KISBroker()
    return broker.submit(instruction)
