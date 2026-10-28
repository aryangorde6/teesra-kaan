"""Plays a transcribed call to the Listener on a clock, as the live page would hear it.

Words reach the transcript `transcribe_delay` seconds after they're spoken. The
judge is asked when a caller turn ends and every `check_every` seconds inside a
long turn, one question at a time: if the judge is busy, the next check waits and
then sees everything heard by then. Judge latency is fixed, or measured from the
real call when `judge_latency` is None, so timings include the model's own delay.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import TextIO

from .judge import Judge
from .listener import Listener
from .signals import Level
from .transcript import LISTENER, Call


@dataclass(frozen=True)
class Timing:
    transcribe_delay: float = 1.0  # s from a word being spoken to it being in the transcript
    judge_latency: float | None = 1.5  # s per judge answer; None = measure the real call
    check_every: float = 6.0  # s of caller speech between checks inside a long turn
    min_new_words: int = 3  # skip a mid-turn check with fewer new caller words than this


@dataclass
class SimResult:
    call: Call
    listener: Listener

    @property
    def t_warn(self) -> float | None:
        """When the first warning (amber or red) was on screen."""
        return self.listener.first_time(Level.AMBER)

    @property
    def t_red(self) -> float | None:
        return self.listener.first_time(Level.RED)

    @property
    def level(self) -> Level:
        return self.listener.alarm.level


def check_points(call: Call, timing: Timing) -> list[tuple[float, bool]]:
    """(time, turn ended) for every moment the judge would be asked."""
    points = []
    for turn in call.turns:
        if turn.speaker == LISTENER:
            continue
        t = turn.start + timing.check_every
        while t < turn.end:
            points.append((t + timing.transcribe_delay, False))
            t += timing.check_every
        points.append((turn.heard_end(timing.transcribe_delay), True))
    return sorted(points)


def simulate(call: Call, judge: Judge, timing: Timing = Timing(), stop_at_red: bool = False, **listener) -> SimResult:
    """`listener` passes options to the Listener, e.g. the free-form rule for comparison B."""
    listener = Listener(judge, **listener)
    words = call.timed_words(timing.transcribe_delay)
    i = 0
    judge_free = 0.0
    for point, turn_ended in check_points(call, timing):
        now = max(point, judge_free)
        while i < len(words) and words[i][0] <= now:
            listener.hear(*words[i][1:])
            i += 1
        if not turn_ended and listener.new_caller_words() < timing.min_new_words:
            continue
        update = listener.check(now, timing.judge_latency)
        if update:
            judge_free = update.t
            if stop_at_red and update.alarm.level == Level.RED:
                break
    while i < len(words):
        listener.hear(*words[i][1:])
        i += 1
    return SimResult(call, listener)


def replay(result: SimResult, out: TextIO | None = None, speed: float | None = 1.0, delay: float = 1.0) -> None:
    """Prints the call and the warnings in time order; sleeps between them unless speed is None."""
    out = out or sys.stdout
    events: list[tuple[float, str]] = []
    caller = result.call.caller_label()
    for turn in result.call.turns:
        who = "caller" if turn.speaker == caller else "you"
        events.append((turn.end + delay, f"{who:>6}: {turn.text}"))
    for update in result.listener.updates:
        for f in update.new:
            events.append((update.t, f"        + {f.id} ({f.said_at:.0f}s): \"{f.quote}\""))
        if update.raised:
            events.append((update.t, f"  >>> {update.alarm.level.name} ({update.alarm.rule})"))
    events.sort(key=lambda e: e[0])
    clock = 0.0
    for t, text in events:
        if speed:
            time.sleep(max(t - clock, 0) / speed)
        clock = max(clock, t)
        print(f"[{int(t // 60)}:{t % 60:04.1f}] {text}", file=out, flush=True)
