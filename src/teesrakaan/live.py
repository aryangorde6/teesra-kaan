"""A live call: transcriber events in, page events out, through the same Listener as everything else.

Partial transcripts can still change, so a word is passed to the Listener only once
it's stable: unchanged across two partials, and not the last word of the partial. A
completed turn commits the rest. Words wait in a buffer until the next check, so the
judge, which runs in a worker thread, never reads a transcript that's being written.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from .judge import Judge
from .listener import Listener
from .messages import SIGNAL_NAME, prediction_events, warning
from .report import build_report
from .signals import Level
from .transcript import Call, Turn


@dataclass
class _Turn:
    speaker: str = "A"
    committed: int = 0
    previous: list[str] = field(default_factory=list)


class LiveCall:
    def __init__(self, judge: Judge, lang: str = "en", check_every: float = 6.0, min_new_words: int = 3) -> None:
        self.listener = Listener(judge)
        self.lang = lang
        self.check_every = check_every
        self.min_new_words = min_new_words
        self.turns: dict[str, _Turn] = {}
        self.current: str | None = None
        self.pending: list[tuple[float, str, str]] = []  # (said, speaker, word) not yet given to the Listener
        self.last_check = 0.0
        self.turn_done = False
        self.quotes: dict[str, str] = {}
        self.counts: dict[str, int] = {}  # words per speaker, kept on the event loop's side
        self._lock = threading.Lock()  # guards `pending` between the event loop and the judge's thread

    def _who(self, speaker: str) -> str:
        """The page's colour for a speaker: the caller is whoever has said the most so far."""
        if not self.counts:
            return "caller"
        return "caller" if speaker == max(self.counts, key=self.counts.__getitem__) else "listener"

    def _commit(self, turn: _Turn, words: list[str], upto: int, said: float) -> list[dict]:
        out = []
        for word in words[turn.committed : upto]:
            with self._lock:
                self.pending.append((said, turn.speaker, word))
            self.counts[turn.speaker] = self.counts.get(turn.speaker, 0) + 1
            out.append({"type": "word", "speaker": self._who(turn.speaker), "t": round(said, 2), "word": word})
        turn.committed = max(turn.committed, upto)
        return out

    def on_event(self, e: dict) -> list[dict]:
        """One transcriber event in; the page events it causes out."""
        kind = e.get("type")
        said = (e.get("audioProcessedMs") or 0) / 1000
        if kind == "speechStart":
            self.current = str(e.get("turnId"))
            self.turns[self.current] = _Turn()
            return []
        turn = self.turns.get(self.current or "")
        if turn is None:
            return []
        if kind == "speaker":
            turn.speaker = str(e.get("label") or "A")
            return []
        if kind == "transcript":
            words = (e.get("transcript") or "").split()
            stable = 0
            while stable < min(len(words), len(turn.previous)) and words[stable] == turn.previous[stable]:
                stable += 1
            turn.previous = words
            out = self._commit(turn, words, min(stable, len(words) - 1), said)
            tail = " ".join(words[turn.committed :])
            return out + [{"type": "partial", "speaker": self._who(turn.speaker), "text": tail}]
        if kind == "speechComplete":
            tid = str(e.get("turnId"))
            turn = self.turns.get(tid, turn)
            words = (e.get("transcript") or " ".join(turn.previous)).split()
            self.turn_done = True
            return self._commit(turn, words, len(words), said) + [{"type": "partial", "speaker": "", "text": ""}]
        return []

    def due(self, now: float) -> bool:
        if len(self.pending) < 1:
            return False
        return self.turn_done or (len(self.pending) >= self.min_new_words and now - self.last_check >= self.check_every)

    def check(self, now: float) -> list[dict]:
        """Runs in a worker thread: hand the buffered words to the Listener, ask the judge, report changes."""
        with self._lock:
            batch, self.pending = self.pending, []
        self.turn_done = False
        self.last_check = now
        for said, speaker, word in batch:
            self.listener.hear(said, speaker, word)
        update = self.listener.check(now)
        if update is None:
            return []
        out = []
        for f in update.new:
            self.quotes[f.id] = f.quote
            out.append({"type": "signal", "id": f.id, "name": SIGNAL_NAME[f.id][self.lang],
                        "quote": f.quote, "said_at": round(f.said_at, 1)})
        if update.raised:
            out.append({"type": "alarm", "t": round(update.t, 1), "warning": warning(update.alarm, dict(self.quotes), self.lang)})
        return out + prediction_events(update, self.lang)

    def to_call(self, call_id: str = "live") -> Call:
        turns = tuple(
            Turn(line.speaker, line.words[0][0], line.words[-1][0], line.text, word_times=tuple(t for t, _ in line.words))
            for line in self.listener.transcript.lines
        )
        return Call(call_id, turns)

    def end(self, now: float) -> list[dict]:
        out = self.check(now) if self.pending else []
        call = self.to_call()
        pack = build_report(call, self.listener, self.lang)
        listener = self.listener
        out.append({
            "type": "end",
            "timing": {"t_warn": listener.first_time(Level.AMBER), "t_red": listener.first_time(Level.RED),
                       "t0": None, "t_ask": None},
            "report": pack.to_dict(),
            "report_markdown": pack.to_markdown(),
        })
        return out
