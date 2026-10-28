"""The numbers in docs/evaluation-rule.md, with Wilson 95% intervals for every rate."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate(k: int, n: int) -> str:
    """'9/10 (60–98%)': the count first, then the interval, never a bare percentage."""
    if n == 0:
        return "0/0"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({round(lo * 100)}–{round(hi * 100)}%)"


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear interpolation between ranks, as numpy's default."""
    if not values:
        return None
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


@dataclass(frozen=True)
class Outcome:
    call_id: str
    set: str
    is_scam: bool
    level: int  # 0 none, 1 amber, 2 red (the highest reached)
    t_warn: float | None = None  # first amber or red
    t_red: float | None = None
    t0: float | None = None  # labelled first scam move
    t_ask: float | None = None  # labelled first ask
    language: str = ""


def summarize(outcomes: Iterable[Outcome]) -> dict:
    rows = list(outcomes)
    scams = [o for o in rows if o.is_scam]
    genuine = [o for o in rows if not o.is_scam]
    red = sum(o.level >= 2 for o in scams)
    any_ = sum(o.level >= 1 for o in scams)

    lead = [o.t_warn - o.t0 for o in scams if o.t_warn is not None and o.t0 is not None]
    lead_red = [o.t_red - o.t0 for o in scams if o.t_red is not None and o.t0 is not None]
    with_ask = [o for o in scams if o.t_ask is not None]
    before_ask = sum(o.t_warn is not None and o.t_warn < o.t_ask for o in with_ask)

    return {
        "scam_calls": len(scams),
        "genuine_calls": len(genuine),
        "caught_red": {"k": red, "n": len(scams), "text": rate(red, len(scams))},
        "caught_red_or_amber": {"k": any_, "n": len(scams), "text": rate(any_, len(scams))},
        "false_alarms_red": {
            "k": sum(o.level >= 2 for o in genuine),
            "n": len(genuine),
            "text": rate(sum(o.level >= 2 for o in genuine), len(genuine)),
        },
        "false_alarms_amber": {
            "k": sum(o.level == 1 for o in genuine),
            "n": len(genuine),
            "text": rate(sum(o.level == 1 for o in genuine), len(genuine)),
        },
        "seconds_to_warning": {
            "n": len(lead),
            "median": percentile(lead, 0.5),
            "p90": percentile(lead, 0.9),
        },
        "seconds_to_red": {
            "n": len(lead_red),
            "median": percentile(lead_red, 0.5),
            "p90": percentile(lead_red, 0.9),
        },
        "warned_before_ask": {
            "k": before_ask,
            "n": len(with_ask),
            "text": rate(before_ask, len(with_ask)),
        },
    }


def summarize_by(outcomes: Iterable[Outcome], key: str) -> dict[str, dict]:
    """The same summary per set or per language. Sets are never pooled into one headline."""
    groups: dict[str, list[Outcome]] = {}
    for o in outcomes:
        groups.setdefault(getattr(o, key), []).append(o)
    return {name: summarize(group) for name, group in sorted(groups.items())}
