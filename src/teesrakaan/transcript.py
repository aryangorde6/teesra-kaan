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
    speaker: str  # CALLER, LISTENER, or a transcriber's speaker label such as "A"
    start: float  # seconds from the start of the call
    end: float
    text: str
    word_times: tuple[float, ...] = ()  # when each word was said, when known
    heard_times: tuple[float, ...] = ()  # when each word reached the transcript, from a real stream

    def words(self) -> list[tuple[float, str]]:
        words = self.text.split()
        if len(self.word_times) == len(words):
            return list(zip(self.word_times, words))
        step = (self.end - self.start) / max(len(words), 1)
        return [(self.start + i * step, w) for i, w in enumerate(words)]

    def heard(self, delay: float) -> list[float]:
        """When each word reached the transcript: recorded from the stream, or said + delay."""
        said = [t for t, _ in self.words()]
        if len(self.heard_times) == len(said):
            return list(self.heard_times)
        return [t + delay for t in said]

    def heard_end(self, delay: float) -> float:
        """When the whole turn was in the transcript."""
        if self.heard_times and len(self.heard_times) == len(self.text.split()):
            return self.heard_times[-1]
        return self.end + delay


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

    def timed_words(self, delay: float) -> list[tuple[float, float, str, str]]:
        """(heard, said, speaker, word), in the order they reached the transcript."""
        items = [
            (heard, said, turn.speaker, w)
            for turn in self.turns
            for (said, w), heard in zip(turn.words(), turn.heard(delay))
        ]
        return sorted(items, key=lambda item: (item[0], item[1]))

    def caller_label(self) -> str:
        """CALLER when the turns say so; otherwise the speaker who said the most."""
        counts: dict[str, int] = {}
        for turn in self.turns:
            counts[turn.speaker] = counts.get(turn.speaker, 0) + len(turn.text.split())
        if CALLER in counts or not counts:
            return CALLER
        return max(counts, key=counts.__getitem__)


def load_call(path: str | Path) -> Call:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    turns = tuple(
        Turn(
            speaker=t["speaker"],
            start=float(t["start"]),
            end=float(t["end"]),
            text=t["text"],
            word_times=tuple(float(x) for x in t.get("word_times", ())),
            heard_times=tuple(float(x) for x in t.get("heard_times", ())),
        )
        for t in data["turns"]
    )
    for turn in turns:
        if not turn.speaker.strip():
            raise ValueError(f"{path}: every turn needs a speaker")
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
    """What has been heard so far, as it grows word by word.

    With a transcriber's speaker labels ("A", "B"), the caller is whoever has said
    the most so far: decided only from what's been heard, so it can change early on.
    """

    def __init__(self) -> None:
        self.lines: list[Line] = []
        self.n_words = 0
        self.words_by_speaker: dict[str, int] = {}

    def add(self, t: float, speaker: str, word: str) -> None:
        if self.lines and self.lines[-1].speaker == speaker:
            self.lines[-1].words.append((t, word))
        else:
            self.lines.append(Line(speaker, [(t, word)]))
        self.n_words += 1
        self.words_by_speaker[speaker] = self.words_by_speaker.get(speaker, 0) + 1

    @property
    def caller(self) -> str:
        counts = self.words_by_speaker
        if CALLER in counts or not counts:
            return CALLER
        return max(counts, key=counts.__getitem__)

    @property
    def n_caller_words(self) -> int:
        return self.words_by_speaker.get(self.caller, 0)

    def dialogue(self) -> str:
        caller = self.caller
        return "\n".join(f"{'CALLER' if line.speaker == caller else 'YOU'}: {line.text}" for line in self.lines)

    def caller_text(self) -> str:
        caller = self.caller
        return " ".join(line.text for line in self.lines if line.speaker == caller)

    def _caller_tokens(self) -> list[tuple[str, float]]:
        tokens = []
        caller = self.caller
        for line in self.lines:
            if line.speaker == caller:
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
