from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from asyncio import Queue
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
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
        return {
            'ts': self.ts,
            'kind': self.kind,
            'level': self.level,
            'message': self.message,
            'symbol': self.symbol,
            'price': self.price,
            'signal': self.signal,
            'confidence': self.confidence,
            'quantity': self.quantity,
            'return_pct': self.return_pct,
            'source': self.source,
            'meta': self.meta,
        }


class SQLiteEventStore:
    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    symbol TEXT,
                    price REAL,
                    signal TEXT,
                    confidence REAL,
                    quantity INTEGER,
                    return_pct REAL,
                    source TEXT,
                    meta_json TEXT NOT NULL
                )
                '''
            )
            self._conn.execute('CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC)')
            self._conn.execute('CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind)')
            self._conn.execute('CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol)')
            self._conn.commit()

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
    ) -> dict[str, Any]:
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
        data = event.to_dict()
        with self._lock:
            self._conn.execute(
                '''
                INSERT INTO events (
                    ts, kind, level, message, symbol, price, signal,
                    confidence, quantity, return_pct, source, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    data['ts'],
                    data['kind'],
                    data['level'],
                    data['message'],
                    data['symbol'],
                    data['price'],
                    data['signal'],
                    data['confidence'],
                    data['quantity'],
                    data['return_pct'],
                    data['source'],
                    json.dumps(data['meta'], ensure_ascii=False),
                ),
            )
            self._conn.commit()
        return data

    def list(
        self,
        *,
        limit: int = 100,
        kind: str | None = None,
        level: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if kind:
            clauses.append('kind = ?')
            params.append(kind)
        if level:
            clauses.append('level = ?')
            params.append(level)
        if query:
            clauses.append('(LOWER(message) LIKE ? OR LOWER(kind) LIKE ? OR LOWER(COALESCE(symbol, "")) LIKE ?)')
            q = f'%{query.lower()}%'
            params.extend([q, q, q])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        sql = f'''
            SELECT ts, kind, level, message, symbol, price, signal, confidence, quantity, return_pct, source, meta_json
            FROM events
            {where}
            ORDER BY id DESC
            LIMIT ?
        '''
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append({
                'ts': row['ts'],
                'kind': row['kind'],
                'level': row['level'],
                'message': row['message'],
                'symbol': row['symbol'],
                'price': row['price'],
                'signal': row['signal'],
                'confidence': row['confidence'],
                'quantity': row['quantity'],
                'return_pct': row['return_pct'],
                'source': row['source'],
                'meta': json.loads(row['meta_json'] or '{}'),
            })
        return out

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute('SELECT COUNT(*) AS count FROM events').fetchone()
        return int(row['count']) if row else 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class RealtimeHub:
    def __init__(self) -> None:
        self._subscribers: set[Queue[dict[str, Any]]] = set()
        self._lock = RLock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> Queue[dict[str, Any]]:
        queue: Queue[dict[str, Any]] = Queue()
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: dict[str, Any]) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._fanout, event)

    def _fanout(self, event: dict[str, Any]) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            with suppress(Exception):
                queue.put_nowait(event)


class TradingEventService:
    def __init__(self, store: SQLiteEventStore, hub: RealtimeHub) -> None:
        self.store = store
        self.hub = hub

    def record(self, **kwargs: Any) -> dict[str, Any]:
        event = self.store.record(**kwargs)
        self.hub.publish(event)
        return event

    def list(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.store.list(**kwargs)

    def count(self) -> int:
        return self.store.count()
