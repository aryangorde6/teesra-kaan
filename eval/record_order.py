"""The order people record the IN test cards and the paraphrase cards in, fixed before the first take
(docs/evaluation-rule.md, v1.6). Recording may stop before the end of a list; whatever is recorded and
labelled by then is run once, so a seeded order, not a choice, decides which calls are in.

    python eval/record_order.py   # writes eval/scripts/record-order.csv

Two lists, each shuffled with seed 20261102:
- `test`: the 42 test scripts, scam and genuine interleaved in proportion (24 to 18), so a list cut short
  still holds both, in about the same ratio.
- `paraphrase`: the 10 paraphrase cards, which one person can record alone (solo takes).
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from teesrakaan.scripts import load_scripts, load_split  # noqa: E402

SEED = 20261102
SCRIPTS = ROOT / "eval" / "scripts"


def interleave(groups: list[list[dict]]) -> list[dict]:
    """Take next from whichever group is furthest behind its share of the whole list."""
    out, taken, total = [], [0] * len(groups), sum(len(g) for g in groups)
    for _ in range(total):
        k = min((i for i, g in enumerate(groups) if taken[i] < len(g)),
                key=lambda i: ((taken[i] + 1) / len(groups[i]), i))
        out.append(groups[k][taken[k]])
        taken[k] += 1
    return out


def main() -> None:
    rng = random.Random(SEED)
    split = load_split(SCRIPTS / "split.csv")
    groups = []
    for name in ("in-scam.json", "in-genuine.json"):
        group = sorted((s for s in load_scripts(SCRIPTS / name) if split[s["id"]] == "test"), key=lambda s: s["id"])
        rng.shuffle(group)
        groups.append(group)
    paraphrase = sorted(load_scripts(SCRIPTS / "in-paraphrase.json"), key=lambda s: s["id"])
    rng.shuffle(paraphrase)

    rows = [("test", s) for s in interleave(groups)] + [("paraphrase", s) for s in paraphrase]
    with open(SCRIPTS / "record-order.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["n", "id", "split", "set", "language", "pattern"])
        n = {"test": 0, "paraphrase": 0}
        for part, s in rows:
            n[part] += 1
            w.writerow([n[part], s["id"], part, s["set"], s["language"], s.get("pattern", 0)])
    print(f"{len(rows)} cards: {n['test']} test, {n['paraphrase']} paraphrase -> {SCRIPTS / 'record-order.csv'}")


if __name__ == "__main__":
    main()
