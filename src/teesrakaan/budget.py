"""Spending ledger with a hard stop, checked against Meta's own meter.

Every paid call reserves its worst-case cost before it is sent and settles to the
actual cost afterwards. The ledger is a SQLite file, so separate processes share
one total. A call whose outcome is unknown (timeout, dropped connection) keeps
its reservation as spent.

A call is refused unless all of these hold (docs/spending.md):
- Our count: spent + reserved + this call's worst case stays within $100 of the
  $150 credits, and within its scope's share (the web page gets $5 of it).
- Meta's meter: a reading of dev.meta.ai -> Billing was recorded within the last
  $10 of spend and 24 hours, it showed a balance of 0, and it wasn't ahead of our
  count by more than $5. Whichever count is higher is the one used.
- The date: paid calls end before the credits' window can.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import config

META_CREDIT_USD = 150.0
# The stop is $100, so $50 of the credits is never touched and nothing reaches the card.
# Config can only lower it.
META_HARD_CEILING_USD = 100.0
METER_EVERY_USD = 10.0  # read Meta's meter again after this much spend
METER_MAX_AGE_S = 24 * 3600
METER_DRIFT_USD = 5.0  # Meta's meter this far ahead of ours: something is spending outside the ledger
# The rules give the credits a 10-day development window from Oct 26; paid calls end
# before it can: Nov 5, 00:00 IST. Config can only make it earlier.
PAID_UNTIL = datetime(2026, 11, 4, 18, 30, tzinfo=timezone.utc)


class BudgetExceeded(RuntimeError):
    pass


class PaidCallsDisabled(RuntimeError):
    pass


SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL,          -- reserved | done | unknown | released
    reserved_usd REAL NOT NULL,
    cost_usd REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    request_id TEXT,
    note TEXT,
    scope TEXT NOT NULL DEFAULT ''
)
"""

METER_SCHEMA = """
CREATE TABLE IF NOT EXISTS meter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    credits_left_usd REAL NOT NULL,  -- dev.meta.ai -> Billing, "Free credits in use"
    balance_inr REAL NOT NULL,       -- dev.meta.ai -> Billing, "Current balance"
    ledger_usd REAL NOT NULL,        -- our own count when it was read
    drift_ok INTEGER NOT NULL DEFAULT 0,
    source TEXT
)
"""


@dataclass(frozen=True)
class Reading:
    ts: float
    credits_left_usd: float
    balance_inr: float
    ledger_usd: float
    drift_ok: bool

    @property
    def meta_spent_usd(self) -> float:
        return META_CREDIT_USD - self.credits_left_usd


@dataclass(frozen=True)
class Summary:
    provider: str
    cap_usd: float
    spent_usd: float
    reserved_usd: float
    calls: int
    counted_usd: float = 0.0  # the higher of our count and Meta's meter
    reading: Reading | None = None
    refusal: str | None = None  # why a $0.01 call would be refused now, if it would

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.cap_usd - max(self.spent_usd, self.counted_usd) - self.reserved_usd)


def meta_cap() -> float:
    configured = config.env_float("TEESRAKAAN_BUDGET_META_USD", META_HARD_CEILING_USD)
    return min(configured, META_HARD_CEILING_USD)


def paid_until() -> datetime:
    raw = config.env("TEESRAKAAN_PAID_UNTIL")
    if not raw:
        return PAID_UNTIL
    configured = datetime.fromisoformat(raw)
    if configured.tzinfo is None:
        raise ValueError("TEESRAKAAN_PAID_UNTIL needs a time zone, e.g. 2026-11-03T18:30+00:00")
    return min(configured, PAID_UNTIL)


def default_ledger_path() -> Path:
    return config.data_dir() / "budget.sqlite"


class Ledger:
    def __init__(
        self,
        provider: str,
        cap_usd: float,
        path: Path | None = None,
        scope: str = "",
        scope_cap_usd: float | None = None,
    ) -> None:
        if cap_usd < 0:
            raise ValueError("cap_usd must be >= 0")
        if provider == "meta":
            cap_usd = min(cap_usd, META_HARD_CEILING_USD)
        self.provider = provider
        self.cap_usd = cap_usd
        self.scope = scope
        self.scope_cap_usd = scope_cap_usd
        self.path = path or default_ledger_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute(SCHEMA)
            db.execute(METER_SCHEMA)
            if "scope" not in {row[1] for row in db.execute("PRAGMA table_info(calls)")}:
                db.execute("ALTER TABLE calls ADD COLUMN scope TEXT NOT NULL DEFAULT ''")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.execute("PRAGMA journal_mode=WAL")
        return db

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = self._connect()
        try:
            yield db
        finally:
            db.close()

    def _committed(self, db: sqlite3.Connection, scope: str | None = None) -> tuple[float, float]:
        where, args = "provider = ?", [self.provider]
        if scope is not None:
            where, args = where + " AND scope = ?", args + [scope]
        spent, reserved = db.execute(
            f"""
            SELECT
              COALESCE(SUM(CASE WHEN status = 'done' THEN cost_usd
                                WHEN status = 'unknown' THEN reserved_usd END), 0),
              COALESCE(SUM(CASE WHEN status = 'reserved' THEN reserved_usd END), 0)
            FROM calls WHERE {where}
            """,
            args,
        ).fetchone()
        return spent, reserved

    def _reading(self, db: sqlite3.Connection) -> Reading | None:
        row = db.execute(
            "SELECT ts, credits_left_usd, balance_inr, ledger_usd, drift_ok FROM meter ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return Reading(row[0], row[1], row[2], row[3], bool(row[4])) if row else None

    def _counted(self, db: sqlite3.Connection) -> tuple[float, float, Reading | None]:
        """What we count as spent (the higher of our ledger and Meta's meter plus our spend since), and reserved."""
        spent, reserved = self._committed(db)
        reading = self._reading(db) if self.provider == "meta" else None
        if reading is None:
            return spent, reserved, None
        return max(spent, reading.meta_spent_usd + spent - reading.ledger_usd), reserved, reading

    def _refusal(self, db: sqlite3.Connection, worst_case_usd: float) -> str | None:
        """Why a call costing at most `worst_case_usd` can't be sent now, or None if it can."""
        end = paid_until()
        if time.time() >= end.timestamp():
            return f"Paid calls ended at {end:%Y-%m-%d %H:%M} UTC, before the credits' window can close."
        counted, reserved, reading = self._counted(db)
        if self.provider == "meta":
            spent, _ = self._committed(db)
            if reading is None:
                return ("Meta's meter hasn't been read yet. From dev.meta.ai -> Billing, run: "
                        "teesrakaan meter --credits-left <free credits> --balance-inr <current balance>")
            if reading.balance_inr > 0:
                return (f"Meta's Billing page showed a balance of Rs {reading.balance_inr:.2f}: the card is being "
                        "billed. Every paid call stops until that's understood.")
            if time.time() - reading.ts > METER_MAX_AGE_S:
                return "Meta's meter was last read over 24 hours ago. Read it again (teesrakaan meter)."
            since = spent + reserved + worst_case_usd - reading.ledger_usd
            if since > METER_EVERY_USD:
                return (f"This call would make ${since:.2f} since Meta's meter was last read; it's read again "
                        f"every ${METER_EVERY_USD:.0f}. Run teesrakaan meter.")
            drift = reading.meta_spent_usd - reading.ledger_usd
            if drift > METER_DRIFT_USD and not reading.drift_ok:
                return (f"Meta's meter showed ${drift:.2f} more spent than this ledger: something is spending "
                        "outside it (another machine, or a leaked key). Find it, then record the reading "
                        "again with --drift-ok.")
        if counted + reserved + worst_case_usd > self.cap_usd:
            return (f"{self.provider}: ${counted:.4f} spent + ${reserved:.4f} reserved "
                    f"+ ${worst_case_usd:.4f} for this call would pass the ${self.cap_usd:.2f} cap.")
        if self.scope_cap_usd is not None:
            used = sum(self._committed(db, self.scope))
            if used + worst_case_usd > self.scope_cap_usd:
                return (f"{self.scope or 'this scope'}: ${used:.4f} used + ${worst_case_usd:.4f} for this call "
                        f"would pass its ${self.scope_cap_usd:.2f} share.")
        return None

    def refusal(self, worst_case_usd: float = 0.01) -> str | None:
        """Why a call like this would be refused now (None if it wouldn't), without reserving anything."""
        if not config.paid_calls_allowed():
            return "Paid API calls are off. Set TEESRAKAAN_ALLOW_PAID=1 to allow them."
        with self._db() as db:
            return self._refusal(db, worst_case_usd)

    def reserve(self, model: str, worst_case_usd: float, note: str = "") -> int:
        """Reserve the worst-case cost of one call, or refuse it."""
        if not config.paid_calls_allowed():
            raise PaidCallsDisabled(
                "Paid API calls are off. Set TEESRAKAAN_ALLOW_PAID=1 to allow them."
            )
        if worst_case_usd < 0:
            raise ValueError("worst_case_usd must be >= 0")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            reason = self._refusal(db, worst_case_usd)
            if reason:
                db.execute("ROLLBACK")
                raise BudgetExceeded(reason)
            cursor = db.execute(
                "INSERT INTO calls (ts, provider, model, status, reserved_usd, note, scope) "
                "VALUES (?, ?, ?, 'reserved', ?, ?, ?)",
                (time.time(), self.provider, model, worst_case_usd, note, self.scope),
            )
            db.execute("COMMIT")
            return int(cursor.lastrowid)

    def settle(
        self,
        call_id: int,
        cost_usd: float,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        request_id: str | None = None,
    ) -> None:
        with self._db() as db:
            db.execute(
                "UPDATE calls SET status = 'done', cost_usd = ?, input_tokens = ?, "
                "output_tokens = ?, request_id = ? WHERE id = ?",
                (cost_usd, input_tokens, output_tokens, request_id, call_id),
            )

    def mark_unknown(self, call_id: int) -> None:
        """The call may have been billed: keep the reservation as spent."""
        with self._db() as db:
            db.execute("UPDATE calls SET status = 'unknown' WHERE id = ?", (call_id,))

    def release(self, call_id: int) -> None:
        """The call was rejected before any work was done: free the reservation."""
        with self._db() as db:
            db.execute("UPDATE calls SET status = 'released' WHERE id = ?", (call_id,))

    def record_meter(
        self,
        credits_left_usd: float,
        balance_inr: float,
        source: str = "",
        drift_ok: bool = False,
        ts: float | None = None,
    ) -> Reading:
        """A reading of dev.meta.ai -> Billing: the free credits left, and the balance the card would pay."""
        if not 0 <= credits_left_usd <= META_CREDIT_USD:
            raise ValueError(f"free credits must be between $0 and ${META_CREDIT_USD:.0f}")
        if balance_inr < 0:
            raise ValueError("the balance can't be negative")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            spent, _ = self._committed(db)
            db.execute(
                "INSERT INTO meter (ts, credits_left_usd, balance_inr, ledger_usd, drift_ok, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts if ts is not None else time.time(), credits_left_usd, balance_inr, spent, int(drift_ok), source),
            )
            db.execute("COMMIT")
            return self._reading(db)

    def summary(self) -> Summary:
        with self._db() as db:
            spent, _ = self._committed(db)
            counted, reserved, reading = self._counted(db)
            (calls,) = db.execute(
                "SELECT COUNT(*) FROM calls WHERE provider = ? AND status != 'released'",
                (self.provider,),
            ).fetchone()
        return Summary(self.provider, self.cap_usd, spent, reserved, calls, counted, reading, self.refusal())
