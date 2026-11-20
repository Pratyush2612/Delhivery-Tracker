from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

from .config import DATA

IST = timezone(timedelta(hours=5, minutes=30))
DB_PATH = DATA / "tracker.db"


def now_ist() -> datetime:
    return datetime.now(tz=IST)


def iso(dt: datetime | None = None) -> str:
    return (dt or now_ist()).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with tx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                awb TEXT NOT NULL,
                carrier TEXT NOT NULL,
                order_id TEXT DEFAULT '',
                city TEXT DEFAULT '',
                zone TEXT DEFAULT 'tier1',
                sku TEXT DEFAULT '',
                cod INTEGER DEFAULT 0,
                value_inr INTEGER DEFAULT 0,
                raw_status TEXT DEFAULT '',
                status TEXT DEFAULT 'unknown',
                age_hours REAL DEFAULT 0,
                sla_hours INTEGER DEFAULT 72,
                delay_hours REAL DEFAULT 0,
                is_delayed INTEGER DEFAULT 0,
                is_rto_risk INTEGER DEFAULT 0,
                last_error TEXT DEFAULT '',
                last_polled_at TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(awb, carrier)
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                channel TEXT NOT NULL,
                awb TEXT DEFAULT '',
                message TEXT NOT NULL,
                delivered INTEGER DEFAULT 0,
                sent_at TEXT NOT NULL
            );
            """
        )


def add_shipment(
    awb: str,
    carrier: str,
    order_id: str = "",
    city: str = "",
    sku: str = "",
    cod: bool = False,
    value_inr: int = 0,
    zone: str = "tier1",
    raw_status: str = "",
    status: str = "",
    age_hours: float = 0,
    delay_hours: float = 0,
) -> dict[str, Any]:
    with tx() as conn:
        conn.execute(
            """
            INSERT INTO shipments (awb, carrier, order_id, city, zone, sku, cod, value_inr, sla_hours, created_at, raw_status, status, age_hours, delay_hours, is_delayed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(awb, carrier) DO UPDATE SET
                order_id=excluded.order_id,
                city=excluded.city,
                zone=excluded.zone,
                sku=excluded.sku,
                cod=excluded.cod,
                value_inr=excluded.value_inr,
                raw_status=CASE WHEN excluded.raw_status != '' THEN excluded.raw_status ELSE shipments.raw_status END,
                status=CASE WHEN excluded.status != '' THEN excluded.status ELSE shipments.status END,
                age_hours=CASE WHEN excluded.age_hours > 0 THEN excluded.age_hours ELSE shipments.age_hours END,
                delay_hours=CASE WHEN excluded.delay_hours > 0 THEN excluded.delay_hours ELSE shipments.delay_hours END,
                is_delayed=CASE WHEN excluded.delay_hours > 0 THEN excluded.is_delayed ELSE shipments.is_delayed END
            """,
            (
                awb.strip(),
                carrier,
                order_id,
                city,
                zone,
                sku,
                int(cod),
                value_inr,
                {"metro": 48, "tier1": 72, "tier2": 96, "remote": 144}.get(zone, 72),
                iso(),
                raw_status,
                status or "unknown",
                float(age_hours or 0),
                float(delay_hours or 0),
                1 if float(delay_hours or 0) > 6 else 0,
            ),
        )
        row = conn.execute(
            "SELECT * FROM shipments WHERE awb=? AND carrier=?",
            (awb.strip(), carrier),
        ).fetchone()
    return dict(row)


def list_shipments() -> list[dict[str, Any]]:
    with tx() as conn:
        rows = conn.execute(
            "SELECT * FROM shipments ORDER BY is_rto_risk DESC, is_delayed DESC, delay_hours DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_shipment(awb: str, carrier: str, fields: dict[str, Any]) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    with tx() as conn:
        conn.execute(
            f"UPDATE shipments SET {cols} WHERE awb=? AND carrier=?",
            [*fields.values(), awb, carrier],
        )


def delete_shipment(awb: str, carrier: str) -> None:
    with tx() as conn:
        conn.execute("DELETE FROM shipments WHERE awb=? AND carrier=?", (awb, carrier))


def add_alert(kind: str, channel: str, awb: str, message: str, delivered: bool) -> dict[str, Any]:
    with tx() as conn:
        cur = conn.execute(
            """
            INSERT INTO alerts (kind, channel, awb, message, delivered, sent_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (kind, channel, awb, message, int(delivered), iso()),
        )
        row = conn.execute("SELECT * FROM alerts WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def list_alerts(limit: int = 80) -> list[dict[str, Any]]:
    with tx() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
