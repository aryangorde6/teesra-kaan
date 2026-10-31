"""The numbers in docs/evaluation-rule.md, with Wilson 95% intervals for every rate."""

from __future__ import annotations

import math
from collections import Counter
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
    ftc_class: str = ""  # FTC only: impersonation, sales or other
    # Metric 7, the next line: (step, shown at, said at if it came true, else None)
    predictions: tuple[tuple[str, float, float | None], ...] = ()
    found: tuple[tuple[str, float, float], ...] = ()  # (signal, said at, found at), for the naive guess


def naive_came_true(rows: Sequence[Outcome]) -> int:
    """Metric 7's naive guess, made at the moments the real predictions were shown.

    It names the signal found on the most calls of the set (ties by signal number)
    among those not yet found at that moment, and comes true on the same terms: the
    caller says it at or after that moment. The counts come from the same calls, which
    favours the guess, so it's reported on dev only.
    """
    counts = Counter(sid for o in rows for sid in {f[0] for f in o.found})
    order = sorted(counts, key=lambda sid: (-counts[sid], len(sid), sid))
    k = 0
    for o in rows:
        said = {sid: said_at for sid, said_at, _ in o.found}
        for _, made_at, _ in o.predictions:
            heard = {sid for sid, _, found_at in o.found if found_at <= made_at}
            guess = next((sid for sid in order if sid not in heard), None)
            k += guess in said and said[guess] >= made_at
    return k


def summarize(outcomes: Iterable[Outcome], naive: bool = False) -> dict:
    """`naive` adds metric 7's naive-guess baseline (dev only, see naive_came_true)."""
    rows = list(outcomes)
    scams = [o for o in rows if o.is_scam]
    genuine = [o for o in rows if not o.is_scam]
    red = sum(o.level >= 2 for o in scams)
    any_ = sum(o.level >= 1 for o in scams)

    lead = [o.t_warn - o.t0 for o in scams if o.t_warn is not None and o.t0 is not None]
    lead_red = [o.t_red - o.t0 for o in scams if o.t_red is not None and o.t0 is not None]
    with_ask = [o for o in scams if o.t_ask is not None]
    before_ask = sum(o.t_warn is not None and o.t_warn < o.t_ask for o in with_ask)

    shown = [p for o in rows for p in o.predictions]
    leads = [said - made for _, made, said in shown if said is not None]
    reach = sum(bool(o.predictions) for o in scams)
    on_genuine = sum(len(o.predictions) for o in genuine)
    guessed = naive_came_true(rows) if naive else None

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
        "next_line": {
            "shown": len(shown),
            "came_true": {"k": len(leads), "n": len(shown), "text": rate(len(leads), len(shown))},
            "naive_guess": None if guessed is None else {
                "k": guessed, "n": len(shown), "text": rate(guessed, len(shown)),
            },
            "seconds_ahead": {"n": len(leads), "median": percentile(leads, 0.5)},
            "reach": {"k": reach, "n": len(scams), "text": rate(reach, len(scams))},
            "per_genuine_call": {
                "shown": on_genuine,
                "calls": len(genuine),
                "mean": on_genuine / len(genuine) if genuine else None,
            },
        },
    }


def summarize_by(outcomes: Iterable[Outcome], key: str, naive: bool = False) -> dict[str, dict]:
    """The same summary per set or per language. Sets are never pooled into one headline."""
    groups: dict[str, list[Outcome]] = {}
    for o in outcomes:
        groups.setdefault(getattr(o, key), []).append(o)
    return {name: summarize(group, naive) for name, group in sorted(groups.items())}


def ftc_summary(outcomes: Iterable[Outcome]) -> dict[str, dict]:
    """Warned (red or amber) per FTC class. Sales robocalls are reported, never counted as false alarms."""
    out: dict[str, dict] = {}
    for o in outcomes:
        row = out.setdefault(o.ftc_class, {"n": 0, "warned": 0, "red": 0})
        row["n"] += 1
        row["warned"] += o.level >= 1
        row["red"] += o.level >= 2
    for row in out.values():
        row["warned_text"] = rate(row["warned"], row["n"])
        row["red_text"] = rate(row["red"], row["n"])
    return dict(sorted(out.items()))


def _secs(x: float | None) -> str:
    return "–" if x is None else f"{x:.0f} s"


# The transcription ablations are run C on their own transcripts (docs/runbook.md), named by the folder's ending.
ABLATIONS = {"-nolang": "C without the language hint", "-nokw": "C without keyword biasing"}


def _run_name(r: dict) -> str:
    for ending, name in ABLATIONS.items():
        if str(r.get("calls_from", "")).rstrip("/").endswith(ending):
            return name
    return r["run"]


def results_table(results: list[dict]) -> str:
    """The README and video table: one block per set, one row per run. Sets are never pooled."""
    out = []
    sets = sorted({name for r in results for name in r["by_set"]})
    for name in sets:
        out += [f"**{name}** ({results[0]['split']})", "",
                "| Run | Warned (red or amber) | Red | Red false alarms | Amber false alarms "
                "| Time to warning, median (90th pct) | Time to red, median | Warned before the ask |",
                "|---|---|---|---|---|---|---|---|"]
        for r in results:
            s = r["by_set"].get(name)
            if not s:
                continue
            warn = s["seconds_to_warning"]
            to_warn = f"{_secs(warn['median'])} ({_secs(warn['p90'])})" if warn["median"] is not None else "–"
            out.append(
                f"| {_run_name(r)} | {s['caught_red_or_amber']['text']} | {s['caught_red']['text']} | "
                f"{s['false_alarms_red']['text'] if s['genuine_calls'] else '–'} | "
                f"{s['false_alarms_amber']['text'] if s['genuine_calls'] else '–'} | "
                f"{to_warn} | "
                f"{_secs(s['seconds_to_red']['median'])} | "
                f"{s['warned_before_ask']['text'] if s['warned_before_ask']['n'] else '–'} |"
            )
        out.append("")
        out += _next_line_rows(results, name)
    return "\n".join(out)


def _next_line_rows(results: list[dict], name: str) -> list[str]:
    """Metric 7 for one set. Result files from before the metric existed are left out."""
    rows = [(_run_name(r), r["by_set"][name]["next_line"]) for r in results if "next_line" in r["by_set"].get(name, {})]
    if not rows:
        return []
    out = [f"The next line, **{name}**", "",
           "| Run | Came true | Naive guess (dev only) | Median seconds ahead | Scam calls with one | Per genuine call |",
           "|---|---|---|---|---|---|"]
    for run, n in rows:
        g = n["per_genuine_call"]
        calls = "1 call" if g["calls"] == 1 else f"{g['calls']} calls"
        per_genuine = f"{g['mean']:.2f} ({g['shown']} on {calls})" if g["calls"] else "–"
        out.append(
            f"| {run} | {n['came_true']['text'] if n['shown'] else '–'} | "
            f"{n['naive_guess']['text'] if n['naive_guess'] and n['shown'] else '–'} | "
            f"{_secs(n['seconds_ahead']['median'])} | "
            f"{n['reach']['text'] if n['reach']['n'] else '–'} | {per_genuine} |"
        )
    out.append("")
    return out
