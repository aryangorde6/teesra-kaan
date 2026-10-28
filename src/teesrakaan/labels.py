"""The labelling sheet and the dev/test splits, exactly as docs/evaluation-rule.md fixes them.

Labels are made by listening, before the system's output on that call is seen.
The splits are decided before anything is recorded or downloaded.
"""

from __future__ import annotations

import csv
import hashlib
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

SPLIT_SEED = 20261028
DEV_SHARE = 0.4
FTC_SAMPLE = 200
FTC_DEV = 50

SETS = ("IN-real", "IN-scam", "IN-genuine", "FTC")
FTC_CLASSES = ("impersonation", "sales", "other")
COLUMNS = (
    "call_id", "set", "split", "is_scam", "pattern", "languages",
    "t0", "t_ask", "ftc_class", "labeller", "labelled_at", "notes",
)


@dataclass(frozen=True)
class Label:
    call_id: str
    set: str
    split: str  # dev or test
    is_scam: bool
    pattern: int  # 1-9 from docs/scam-tactics.md; 0 for genuine or none
    languages: str  # e.g. "hi+en"
    t0: float | None  # seconds: the caller's first scam move
    t_ask: float | None  # seconds: the caller's first ask, if any
    ftc_class: str  # FTC only
    labeller: str
    labelled_at: str  # ISO time the label was made
    notes: str = ""


def _seconds(value: str) -> float | None:
    """'' → None; '83.5' or '1:23.5' → seconds."""
    value = value.strip()
    if not value:
        return None
    if ":" in value:
        minutes, seconds = value.split(":", 1)
        return int(minutes) * 60 + float(seconds)
    return float(value)


def _check(row: dict[str, str], line: int) -> list[str]:
    errors = []
    where = f"line {line} ({row.get('call_id', '?')})"
    if row["set"] not in SETS:
        errors.append(f"{where}: set must be one of {SETS}")
    if row["split"] not in ("dev", "test"):
        errors.append(f"{where}: split must be dev or test")
    if row["is_scam"] not in ("0", "1"):
        errors.append(f"{where}: is_scam must be 0 or 1")
    scam = row["is_scam"] == "1"
    if row["set"].startswith("IN") and scam and not row["t0"].strip():
        errors.append(f"{where}: an IN scam call needs t0")
    if not scam and (row["t0"].strip() or row["t_ask"].strip()):
        errors.append(f"{where}: a genuine call has no t0 or t_ask")
    if row["set"] == "FTC" and row["ftc_class"] not in FTC_CLASSES:
        errors.append(f"{where}: FTC calls need ftc_class, one of {FTC_CLASSES}")
    t0, t_ask = _seconds(row["t0"] or ""), _seconds(row["t_ask"] or "")
    if t0 is not None and t_ask is not None and t_ask < t0:
        errors.append(f"{where}: t_ask is before t0")
    if not row["labelled_at"].strip():
        errors.append(f"{where}: labelled_at is required")
    return errors


def read_labels(path: str | Path) -> dict[str, Label]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = set(COLUMNS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        rows = list(reader)
    errors, labels = [], {}
    for line, row in enumerate(rows, start=2):
        row = {k: (v or "") for k, v in row.items()}
        errors += _check(row, line)
        if row["call_id"] in labels:
            errors.append(f"line {line}: duplicate call_id {row['call_id']}")
        labels[row["call_id"]] = Label(
            call_id=row["call_id"],
            set=row["set"],
            split=row["split"],
            is_scam=row["is_scam"] == "1",
            pattern=int(row["pattern"] or 0),
            languages=row["languages"],
            t0=_seconds(row["t0"]),
            t_ask=_seconds(row["t_ask"]),
            ftc_class=row["ftc_class"],
            labeller=row["labeller"],
            labelled_at=row["labelled_at"],
            notes=row["notes"],
        )
    if errors:
        raise ValueError("labelling sheet has errors:\n" + "\n".join(errors))
    return labels


def write_template(path: str | Path, rows: Iterable[dict[str, str]] = ()) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in COLUMNS})


def split_scripts(script_ids: Sequence[str], seed: int = SPLIT_SEED, dev_share: float = DEV_SHARE) -> dict[str, str]:
    """IN-scam or IN-genuine scripts → dev or test. Sorted first, so the input order doesn't matter."""
    ids = sorted(script_ids)
    random.Random(seed).shuffle(ids)
    n_dev = round(len(ids) * dev_share)
    return {sid: ("dev" if i < n_dev else "test") for i, sid in enumerate(ids)}


def sample_ftc(file_names: Iterable[str], n: int = FTC_SAMPLE, n_dev: int = FTC_DEV) -> dict[str, str]:
    """English FTC calls sorted by sha256(file_name); the first n are used, the first n_dev of them dev.

    Duplicate names (one recording listed under two FTC cases) count once.
    """
    ranked = sorted(set(file_names), key=lambda name: hashlib.sha256(name.encode("utf-8")).hexdigest())[:n]
    return {name: ("dev" if i < n_dev else "test") for i, name in enumerate(ranked)}
