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


def cards_markdown(scripts: list[dict], split: dict[str, str]) -> str:
    """Printable cards for the actors, dev scripts first (they're recorded first)."""
    order = sorted(scripts, key=lambda s: (split[s["id"]] != "dev", s["id"]))
    out = ["# Recording cards", "",
           "Say each line in your own words, in order. Keep the made-up names, numbers and amounts.",
           "Record dev cards first. Save each as `<ID>.m4a` (or .wav) in the folder for its split.", ""]
    for s in order:
        what = f"pattern {s['pattern']}" if "pattern" in s else s.get("kind", "")
        out.append(f"## {s['id']} · {split[s['id']]} · {s['language']} · {what}")
        if roles := s.get("roles"):
            out.append(f"_Caller: {roles['caller']}. Listener: {roles['listener']}._")
        out.append("")
        for speaker, text, *how in s["lines"]:
            note = f" _({how[0]})_" if how else ""
            out.append(f"- **{speaker.capitalize()}**{note}: {text}")
        out.append("")
    return "\n".join(out)
