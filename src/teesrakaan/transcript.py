"""Calls, turns and the transcript heard so far, with quotes mapped back to the moment they were said."""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from pathlib import Path

CALLER = "caller"
LISTENER = "listener"

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize(text: str) -> str:
    """Lower case, Devanagari digits to ASCII, punctuation to spaces, one space between words."""
    text = unicodedata.normalize("NFC", text).translate(_DEVANAGARI_DIGITS).lower()
    kept = "".join(ch if unicodedata.category(ch)[0] in "LMN" else " " for ch in text)
    return " ".join(kept.split())


@dataclass(frozen=True)
class Turn:
    speaker: str  # CALLER or LISTENER
    start: float  # seconds from the start of the call
    end: float
    text: str
    word_times: tuple[float, ...] = ()  # start of each word, when the transcriber gives them

    def words(self) -> list[tuple[float, str]]:
        words = self.text.split()
        if len(self.word_times) == len(words):
            return list(zip(self.word_times, words))
        step = (self.end - self.start) / max(len(words), 1)
        return [(self.start + i * step, w) for i, w in enumerate(words)]


@dataclass(frozen=True)
class Call:
    id: str
    turns: tuple[Turn, ...]
    language: str = ""  # e.g. "hi+en"
    set: str = ""  # IN-real, IN-scam, IN-genuine, FTC, demo
    re_enactment: bool = False
    label: dict = field(default_factory=dict)  # optional inline label, for demo calls

    @property
    def duration(self) -> float:
        return max((t.end for t in self.turns), default=0.0)

    def words(self) -> Iterator[tuple[float, str, str]]:
        """(time, speaker, word) for the whole call, in time order."""
        items = [(t, turn.speaker, w) for turn in self.turns for t, w in turn.words()]
        yield from sorted(items, key=lambda item: item[0])


def load_call(path: str | Path) -> Call:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    turns = tuple(
        Turn(
            speaker=t["speaker"],
            start=float(t["start"]),
            end=float(t["end"]),
            text=t["text"],
            word_times=tuple(float(x) for x in t.get("word_times", ())),
        )
        for t in data["turns"]
    )
    for turn in turns:
        if turn.speaker not in (CALLER, LISTENER):
            raise ValueError(f"{path}: speaker must be {CALLER!r} or {LISTENER!r}, not {turn.speaker!r}")
    return Call(
        id=data["id"],
        turns=turns,
        language=data.get("language", ""),
        set=data.get("set", ""),
        re_enactment=bool(data.get("re_enactment", False)),
        label=data.get("label", {}),
    )


def merge_speakers(call: Call) -> Call:
    """The ablation without speaker separation: every word is treated as the caller's."""
    return replace(call, turns=tuple(replace(t, speaker=CALLER) for t in call.turns))


@dataclass
class Line:
    speaker: str
    words: list[tuple[float, str]]

    @property
    def start(self) -> float:
        return self.words[0][0]

    @property
    def text(self) -> str:
        return " ".join(w for _, w in self.words)


class Transcript:
    """What has been heard so far, as it grows word by word."""

    def __init__(self) -> None:
        self.lines: list[Line] = []
        self.n_words = 0
        self.n_caller_words = 0

    def add(self, t: float, speaker: str, word: str) -> None:
        if self.lines and self.lines[-1].speaker == speaker:
            self.lines[-1].words.append((t, word))
        else:
            self.lines.append(Line(speaker, [(t, word)]))
        self.n_words += 1
        self.n_caller_words += speaker == CALLER

    def dialogue(self) -> str:
        who = {CALLER: "CALLER", LISTENER: "YOU"}
        return "\n".join(f"{who[line.speaker]}: {line.text}" for line in self.lines)

    def caller_text(self) -> str:
        return " ".join(line.text for line in self.lines if line.speaker == CALLER)

    def _caller_tokens(self) -> list[tuple[str, float]]:
        tokens = []
        for line in self.lines:
            if line.speaker == CALLER:
                for t, w in line.words:
                    tokens.extend((tok, t) for tok in normalize(w).split())
        return tokens

    def locate(self, quote: str) -> float | None:
        """When the caller started saying `quote`, or None if the caller never said it."""
        wanted = normalize(quote).split()
        if not wanted:
            return None
        tokens = self._caller_tokens()
        words = [tok for tok, _ in tokens]
        n = len(wanted)
        for i in range(len(words) - n + 1):
            if words[i : i + n] == wanted:
                return tokens[i][1]
        return None
