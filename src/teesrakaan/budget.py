"""Spending ledger with a hard stop.

Every paid call reserves its worst-case cost before it is sent and settles to the
actual cost afterwards. The ledger is a SQLite file, so separate processes share
one total. A call whose outcome is unknown (timeout, dropped connection) keeps
its reservation as spent.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import config

# The Meta credit is $150; the stop is $120 (docs/evaluation-rule.md). Config can only lower it.
META_HARD_CEILING_USD = 120.0


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
    note TEXT
)
"""


@dataclass(frozen=True)
class Summary:
    provider: str
    cap_usd: float
    spent_usd: float
    reserved_usd: float
    calls: int

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.cap_usd - self.spent_usd - self.reserved_usd)


def meta_cap() -> float:
    configured = config.env_float("TEESRAKAAN_BUDGET_META_USD", META_HARD_CEILING_USD)
    return min(configured, META_HARD_CEILING_USD)


def default_ledger_path() -> Path:
    return config.data_dir() / "budget.sqlite"


class Ledger:
    def __init__(self, provider: str, cap_usd: float, path: Path | None = None) -> None:
        if cap_usd < 0:
            raise ValueError("cap_usd must be >= 0")
        if provider == "meta":
            cap_usd = min(cap_usd, META_HARD_CEILING_USD)
        self.provider = provider
        self.cap_usd = cap_usd
        self.path = path or default_ledger_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute(SCHEMA)

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

    def _committed(self, db: sqlite3.Connection) -> tuple[float, float]:
        spent, reserved = db.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN status = 'done' THEN cost_usd
                                WHEN status = 'unknown' THEN reserved_usd END), 0),
              COALESCE(SUM(CASE WHEN status = 'reserved' THEN reserved_usd END), 0)
            FROM calls WHERE provider = ?
            """,
            (self.provider,),
        ).fetchone()
        return spent, reserved

    def reserve(self, model: str, worst_case_usd: float, note: str = "") -> int:
        """Reserve the worst-case cost of one call, or refuse it."""
        if not config.paid_calls_allowed():
            raise PaidCallsDisabled(
                "Paid API calls are off. Set TEESRAKAAN_ALLOW_PAID=1 to allow them."
            )
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            spent, reserved = self._committed(db)
            if spent + reserved + worst_case_usd > self.cap_usd:
                db.execute("ROLLBACK")
                raise BudgetExceeded(
                    f"{self.provider}: ${spent:.4f} spent + ${reserved:.4f} reserved "
                    f"+ ${worst_case_usd:.4f} for this call would pass the "
                    f"${self.cap_usd:.2f} cap."
                )
            cursor = db.execute(
                "INSERT INTO calls (ts, provider, model, status, reserved_usd, note) "
                "VALUES (?, ?, ?, 'reserved', ?, ?)",
                (time.time(), self.provider, model, worst_case_usd, note),
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

    def summary(self) -> Summary:
        with self._db() as db:
            spent, reserved = self._committed(db)
            (calls,) = db.execute(
                "SELECT COUNT(*) FROM calls WHERE provider = ? AND status != 'released'",
                (self.provider,),
            ).fetchone()
        return Summary(self.provider, self.cap_usd, spent, reserved, calls)

