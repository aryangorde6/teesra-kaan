"""Scam scripts as ordered steps, and the caller's next line they predict.

Every pattern in docs/scam-tactics.md is a script: the same steps, in roughly the
same order, on every call. Once a call has matched two steps of a script, the
caller's next step can be named before it's said ("next, he will tell you not to
tell anyone"). When the caller then says it, the page shows the prediction came
true: proof, in the caller's own words, that they're reading a script.

Fixed scripts from the advisories make the prediction, not a model, as in signals.py.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

PLAYBOOK_VERSION = "v1 (Oct 28, 2026)"
MIN_STEPS = 2  # steps of a script heard before it may predict


@dataclass(frozen=True)
class Script:
    id: str
    name: str
    pattern: int  # its row in docs/scam-tactics.md
    steps: tuple[str, ...]  # signal ids, in the order the call usually goes


# The order of each script is the "How the call goes" column of docs/scam-tactics.md.
SCRIPTS: tuple[Script, ...] = (
    Script("digital-arrest", "Digital arrest", 1, ("A1", "A2", "A8", "A4", "A6")),
    # "It's usually the opening of pattern 1", so it runs on into pattern 1's steps.
    Script("parcel", "Courier or customs parcel", 2, ("A10", "A9", "A1", "A2", "A8", "A4", "A6")),
    Script("number-block", "Your number will be blocked", 3, ("A1", "A2", "A3", "A10", "A5")),
    Script("kyc", "KYC update or account block", 4, ("A1", "A2", "A3", "A5", "A7")),
    Script("pin-to-receive", "Enter PIN to receive money", 5, ("A12", "A6", "A11")),
    Script("fake-care", "Fake customer care or refund", 6, ("A1", "A12", "A7", "A5", "A6")),
    Script("family-emergency", "Family emergency", 7, ("A2", "A3", "A4", "A6")),
    Script("electricity", "Electricity disconnection", 8, ("A1", "A2", "A3", "A6", "A7")),
    Script("prize", "Prize, lottery or KBC", 9, ("A12", "A6")),
)

BY_ID: dict[str, Script] = {s.id: s for s in SCRIPTS}


@dataclass(frozen=True)
class Next:
    step: str  # the signal the caller will say next
    scripts: tuple[str, ...]  # the scripts that agree on it


@dataclass(frozen=True)
class Ahead:
    steps: tuple[str, ...]  # what the caller will do next, in order; empty when the scripts disagree or have run out
    scripts: tuple[str, ...]  # the scripts that match best
    done: bool  # every one of them has run out: the call is past its last step


def _leaders(heard: frozenset[str]) -> list[tuple[str, tuple[str, ...]]]:
    """(script, the steps it has left) for each script with the most steps heard, if at least MIN_STEPS.

    A script's steps left are those after the last one heard that haven't been heard yet.
    """
    best, leaders = 0, []
    for script in SCRIPTS:
        hits = [i for i, step in enumerate(script.steps) if step in heard]
        if len(hits) < MIN_STEPS:
            continue
        # A script that has run out still counts: the call is past anything it can predict.
        rest = tuple(s for s in script.steps[hits[-1] + 1 :] if s not in heard)
        if len(hits) > best:
            best, leaders = len(hits), []
        if len(hits) == best:
            leaders.append((script.id, rest))
    return leaders


def predict(seen: Iterable[str]) -> Next | None:
    """The caller's next step, or None when the scripts don't agree on one.

    A script matches once at least MIN_STEPS of its steps have been heard. Each
    script with the most steps heard names its next step: the first one not yet
    heard after the last one heard, or none if it has run out. A prediction is
    made only when they all name the same step, so after "police" and "FIR"
    alone (a digital arrest, or a KYC or number-block call?) it waits for one
    more step.
    """
    leaders = _leaders(frozenset(seen))
    steps = {rest[0] if rest else None for _, rest in leaders}
    if len(steps) != 1 or None in steps:
        return None
    return Next(steps.pop(), tuple(sid for sid, _ in leaders))


def ahead(seen: Iterable[str]) -> Ahead | None:
    """The rest of the script, for a call told after it happened ("check before you pay"), or None
    when no script matches yet.

    The same best-matching scripts as predict(), but every step they all still agree on, in order,
    so its first step is always predict()'s.
    """
    leaders = _leaders(frozenset(seen))
    if not leaders:
        return None
    shared = []
    for steps in zip(*(rest for _, rest in leaders)):
        if len(set(steps)) > 1:
            break
        shared.append(steps[0])
    return Ahead(tuple(shared), tuple(sid for sid, _ in leaders), all(not rest for _, rest in leaders))
