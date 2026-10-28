"""The third ear: hears the call word by word, asks the judge, checks its quotes, and keeps the alarm.

The same Listener runs in the live page and in the evaluation, so the numbers
measure the code that warns people.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from .judge import Judge
from .playbook import Next, predict
from .signals import SIGNALS, Alarm, Level, Signal, decide
from .transcript import Transcript


@dataclass(frozen=True)
class Found:
    id: str
    quote: str
    said_at: float  # when the caller said it, from the transcript
    found_at: float  # when the listener knew it


@dataclass
class Prediction:
    """The caller's next line, shown before they say it (see playbook.py)."""

    step: str
    made_at: float  # when it was shown
    scripts: tuple[str, ...]
    said_at: float | None = None  # when the caller said it, once they have
    quote: str = ""

    @property
    def came_true(self) -> bool:
        """Said after it was shown. A step found late, but said before, doesn't count."""
        return self.said_at is not None and self.said_at >= self.made_at


@dataclass(frozen=True)
class Update:
    t: float  # when the judge's answer was in
    alarm: Alarm
    new: tuple[Found, ...]
    raised: bool  # the alarm level went up
    next: Prediction | None = None  # the line now predicted, if any
    next_changed: bool = False
    came_true: tuple[Prediction, ...] = ()


@dataclass
class Listener:
    judge: Judge
    signals: tuple[Signal, ...] = SIGNALS
    decide: Callable[[Iterable[str]], Alarm] = decide
    verify_quotes: bool = True  # off only for comparison B, which answers without quotes
    predict: Callable[[Iterable[str]], Next | None] | None = predict
    transcript: Transcript = field(default_factory=Transcript)
    found: dict[str, Found] = field(default_factory=dict)
    alarm: Alarm = field(default_factory=lambda: Alarm(Level.NONE, "", frozenset()))
    updates: list[Update] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (signal, quote) not found in the caller's words
    predictions: list[Prediction] = field(default_factory=list)
    next: Prediction | None = None
    judge_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    _checked_at_words: int = -1

    def hear(self, t: float, speaker: str, word: str) -> None:
        self.transcript.add(t, speaker, word)

    def new_caller_words(self) -> int:
        return self.transcript.n_caller_words - max(self._checked_at_words, 0)

    @property
    def open_questions(self) -> tuple[Signal, ...]:
        return tuple(s for s in self.signals if s.id not in self.found)

    def check(self, asked_at: float, latency: float | None = None) -> Update | None:
        """Ask the judge about what's been heard. `latency` None means the judge's own: recorded, or measured.

        Returns None when there's nothing new to ask about.
        """
        questions = self.open_questions
        if not questions or self.transcript.n_caller_words == self._checked_at_words:
            return None
        self._checked_at_words = self.transcript.n_caller_words
        started = time.monotonic()
        reply = self.judge.ask(questions, self.transcript)
        if latency is None:
            latency = reply.latency if reply.latency is not None else time.monotonic() - started
        done_at = asked_at + latency
        self.judge_calls += 1
        self.input_tokens += reply.input_tokens
        self.output_tokens += reply.output_tokens

        new = []
        for answer in reply.yes:
            if answer.id in self.found:
                continue
            said_at = self.transcript.locate(answer.quote) if self.verify_quotes else done_at
            if said_at is None:
                self.rejected.append((answer.id, answer.quote))
                continue
            found = Found(answer.id, answer.quote, said_at, done_at)
            self.found[answer.id] = found
            new.append(found)

        came_true = []
        for f in new:
            for p in self.predictions:
                if p.step == f.id and p.said_at is None:
                    p.said_at, p.quote = f.said_at, f.quote
                    if p.came_true:
                        came_true.append(p)
        shown = self.next
        self.next = self._predict(done_at)

        alarm = self.decide(self.found)
        raised = alarm.level > self.alarm.level
        if alarm.level >= self.alarm.level:
            self.alarm = alarm
        update = Update(done_at, self.alarm, tuple(new), raised, self.next, self.next is not shown, tuple(came_true))
        self.updates.append(update)
        return update

    def _predict(self, t: float) -> Prediction | None:
        nxt = self.predict(self.found) if self.predict else None
        if nxt is None:
            return None
        for p in self.predictions:
            if p.step == nxt.step and p.said_at is None:
                return p
        p = Prediction(nxt.step, t, nxt.scripts)
        self.predictions.append(p)
        return p

    def first_time(self, level: Level) -> float | None:
        return next((u.t for u in self.updates if u.alarm.level >= level), None)
