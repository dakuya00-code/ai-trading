from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models import MarketSnapshot


def _num(value: Any, default: float = 0.0) -> float:
    if value in (None, ''):
        return default
    try:
        return float(str(value).replace(',', '').strip())
    except Exception:
        return default


def _int(value: Any, default: int = 0) -> int:
    if value in (None, ''):
        return default
    try:
        return int(float(str(value).replace(',', '').strip()))
    except Exception:
        return default


@dataclass(slots=True)
class PortfolioPosition:
    symbol: str
    name: str = ''
    quantity: int = 0
    avg_price: float = 0.0
    sector: str = ''
    memo: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'sector': self.sector,
            'memo': self.memo,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PortfolioPosition':
        return cls(
            symbol=str(data.get('symbol', '')).strip(),
            name=str(data.get('name', '')).strip(),
            quantity=int(data.get('quantity', 0) or 0),
            avg_price=float(data.get('avg_price', 0) or 0),
            sector=str(data.get('sector', '')).strip(),
            memo=str(data.get('memo', '')).strip(),
        )


@dataclass(slots=True)
class PortfolioRow:
    symbol: str
    name: str
    quantity: int
    avg_price: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    sector: str = ''
    memo: str = ''
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'cost_basis': self.cost_basis,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'sector': self.sector,
            'memo': self.memo,
            'updated_at': self.updated_at,
        }


@dataclass(slots=True)
class PortfolioSummary:
    positions: list[PortfolioRow] = field(default_factory=list)
    total_market_value: float = 0.0
    total_cost_basis: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    positions_count: int = 0
    updated_at: str | None = None
    source: str = 'local'

    def to_dict(self) -> dict[str, Any]:
        return {
            'positions': [row.to_dict() for row in self.positions],
            'total_market_value': self.total_market_value,
            'total_cost_basis': self.total_cost_basis,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'positions_count': self.positions_count,
            'updated_at': self.updated_at,
            'source': self.source,
        }


@dataclass(slots=True)
class PortfolioSnapshotResult:
    summary: PortfolioSummary
    source: str

    def to_dict(self) -> dict[str, Any]:
        payload = self.summary.to_dict()
        payload['source'] = self.source
        return payload


class PortfolioStore:
    def __init__(self, path: str | os.PathLike[str] = 'data/portfolio.json') -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._positions = self._load()
        self._last_updated_at: str | None = None

    def _load(self) -> list[PortfolioPosition]:
        env_payload = os.getenv('AI_TRADING_PORTFOLIO_JSON', '').strip()
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding='utf-8'))
            except Exception:
                raw = []
        elif env_payload:
            try:
                raw = json.loads(env_payload)
            except Exception:
                raw = []
        else:
            raw = []
        if isinstance(raw, dict):
            raw = raw.get('positions', [])
        positions: list[PortfolioPosition] = []
        for item in raw or []:
            pos = PortfolioPosition.from_dict(item)
            if pos.symbol:
                positions.append(pos)
        return positions

    def _save(self) -> None:
        payload = {
            'updated_at': self._last_updated_at,
            'positions': [pos.to_dict() for pos in self._positions],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def list(self) -> list[PortfolioPosition]:
        return list(self._positions)

    def upsert(self, position: PortfolioPosition) -> PortfolioPosition:
        position.symbol = position.symbol.strip()
        if not position.symbol:
            raise ValueError('symbol is required')
        replaced = False
        next_positions: list[PortfolioPosition] = []
        for existing in self._positions:
            if existing.symbol == position.symbol:
                next_positions.append(position)
                replaced = True
            else:
                next_positions.append(existing)
        if not replaced:
            next_positions.append(position)
        self._positions = next_positions
        self._last_updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return position

    def remove(self, symbol: str) -> bool:
        symbol = symbol.strip()
        before = len(self._positions)
        self._positions = [pos for pos in self._positions if pos.symbol != symbol]
        if len(self._positions) == before:
            return False
        self._last_updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def _row_for(self, position: PortfolioPosition, snapshot: MarketSnapshot) -> PortfolioRow:
        cost_basis = round(position.quantity * position.avg_price, 2)
        market_value = round(position.quantity * snapshot.price, 2)
        pnl = round(market_value - cost_basis, 2)
        pnl_pct = round((pnl / cost_basis) * 100, 2) if cost_basis else 0.0
        return PortfolioRow(
            symbol=position.symbol,
            name=position.name or position.symbol,
            quantity=position.quantity,
            avg_price=position.avg_price,
            current_price=snapshot.price,
            market_value=market_value,
            cost_basis=cost_basis,
            unrealized_pnl=pnl,
            unrealized_pnl_pct=pnl_pct,
            sector=position.sector,
            memo=position.memo,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def snapshot(self, collector) -> PortfolioSummary:
        rows: list[PortfolioRow] = []
        total_market_value = 0.0
        total_cost_basis = 0.0
        for position in self._positions:
            try:
                snapshot = collector.fetch_snapshot(position.symbol)
            except Exception:
                fallback = MarketSnapshot(
                    symbol=position.symbol,
                    price=position.avg_price or 0.0,
                    moving_average_short=position.avg_price or 0.0,
                    moving_average_long=position.avg_price or 0.0,
                    rsi=None,
                    sentiment=None,
                    volume=None,
                )
                row = self._row_for(position, fallback)
            else:
                row = self._row_for(position, snapshot)
            rows.append(row)
            total_market_value += row.market_value
            total_cost_basis += row.cost_basis
        pnl = round(total_market_value - total_cost_basis, 2)
        pnl_pct = round((pnl / total_cost_basis) * 100, 2) if total_cost_basis else 0.0
        updated_at = datetime.now(timezone.utc).isoformat() if rows else self._last_updated_at
        return PortfolioSummary(
            positions=rows,
            total_market_value=round(total_market_value, 2),
            total_cost_basis=round(total_cost_basis, 2),
            unrealized_pnl=pnl,
            unrealized_pnl_pct=pnl_pct,
            positions_count=len(rows),
            updated_at=updated_at,
            source='local',
        )


def summary_from_live_holdings(holdings_payload: dict[str, Any]) -> PortfolioSummary:
    rows: list[PortfolioRow] = []
    total_market_value = 0.0
    total_cost_basis = 0.0
    holdings = holdings_payload.get('holdings') or []
    for item in holdings:
        symbol = str(item.get('pdno') or item.get('symbol') or '').strip()
        if not symbol:
            continue
        name = str(item.get('prdt_name') or item.get('name') or symbol).strip()
        quantity = _int(item.get('hldg_qty') or item.get('quantity') or item.get('qty'))
        avg_price = _num(item.get('pchs_avg_pric') or item.get('avg_price') or item.get('buy_price'))
        current_price = _num(item.get('prpr') or item.get('stck_prpr') or item.get('evlu_pric') or item.get('current_price') or avg_price)
        market_value = _num(item.get('evlu_amt') or item.get('market_value') or quantity * current_price)
        cost_basis = _num(item.get('pchs_amt') or item.get('cost_basis') or quantity * avg_price)
        unrealized_pnl = _num(item.get('evlu_pfls_amt') or item.get('unrealized_pnl') or (market_value - cost_basis))
        unrealized_pnl_pct = _num(item.get('evlu_pfls_rt') or item.get('unrealized_pnl_pct') or ((unrealized_pnl / cost_basis) * 100 if cost_basis else 0.0))
        row = PortfolioRow(
            symbol=symbol,
            name=name,
            quantity=quantity,
            avg_price=avg_price,
            current_price=current_price,
            market_value=round(market_value, 2),
            cost_basis=round(cost_basis, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            unrealized_pnl_pct=round(unrealized_pnl_pct, 2),
            sector=str(item.get('sector') or ''),
            memo=str(item.get('memo') or ''),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        rows.append(row)
        total_market_value += row.market_value
        total_cost_basis += row.cost_basis
    pnl = round(total_market_value - total_cost_basis, 2)
    pnl_pct = round((pnl / total_cost_basis) * 100, 2) if total_cost_basis else 0.0
    updated_at = datetime.now(timezone.utc).isoformat() if rows else None
    return PortfolioSummary(
        positions=rows,
        total_market_value=round(total_market_value, 2),
        total_cost_basis=round(total_cost_basis, 2),
        unrealized_pnl=pnl,
        unrealized_pnl_pct=pnl_pct,
        positions_count=len(rows),
        updated_at=updated_at,
        source='kis-live',
    )
