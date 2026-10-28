"""Re-enactment scripts, and rough call files made from them for offline runs before anything is recorded.

The timings here are estimates (about 2.6 words a second, 0.6 s between turns).
Real numbers come only from recordings, labelled by listening.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .transcript import Call, Turn

WORDS_PER_SECOND = 2.6
GAP = 0.6


def load_scripts(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [{**s, "set": data["set"]} for s in data["scripts"]]


def load_split(path: str | Path) -> dict[str, str]:
    with open(path, newline="", encoding="utf-8") as f:
        return {row["id"]: row["split"] for row in csv.DictReader(f)}


def to_call(script: dict) -> Call:
    t, turns = 0.0, []
    for speaker, text, *_ in script["lines"]:
        length = max(len(text.split()) / WORDS_PER_SECOND, 0.8)
        turns.append(Turn(speaker, round(t, 2), round(t + length, 2), text))
        t += length + GAP
    return Call(
        id=script["id"],
        turns=tuple(turns),
        language=script["language"],
        set=script["set"],
        re_enactment=True,
        label={"is_scam": script["set"] == "IN-scam", "pattern": script.get("pattern", 0)},
    )
