from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass(slots=True)
class Event:
    ts: str
    kind: str
    level: str
    message: str
    symbol: str | None = None
    price: float | None = None
    signal: str | None = None
    confidence: float | None = None
    quantity: int | None = None
    return_pct: float | None = None
    source: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventStore:
    def __init__(self, maxlen: int = 300) -> None:
        self._events: deque[Event] = deque(maxlen=maxlen)
        self._lock = Lock()

    def record(
        self,
        *,
        kind: str,
        message: str,
        level: str = 'info',
        symbol: str | None = None,
        price: float | None = None,
        signal: str | None = None,
        confidence: float | None = None,
        quantity: int | None = None,
        return_pct: float | None = None,
        source: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(
            ts=datetime.now(timezone.utc).isoformat(),
            kind=kind,
            level=level,
            message=message,
            symbol=symbol,
            price=price,
            signal=signal,
            confidence=confidence,
            quantity=quantity,
            return_pct=return_pct,
            source=source,
            meta=meta or {},
        )
        with self._lock:
            self._events.append(event)
        return event

    def list(self, *, limit: int = 100, kind: str | None = None, level: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._events)
        if kind:
            items = [item for item in items if item.kind == kind]
        if level:
            items = [item for item in items if item.level == level]
        if query:
            q = query.lower()
            items = [item for item in items if q in item.message.lower() or q in item.kind.lower() or q in (item.symbol or '').lower()]
        return [item.to_dict() for item in items[-limit:]][::-1]

    def count(self) -> int:
        with self._lock:
            return len(self._events)
