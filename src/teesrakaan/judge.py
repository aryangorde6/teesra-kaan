"""Judges answer the signal questions about the transcript so far. They never decide the alarm.

Every "yes" must quote the caller. The listener checks that quote against what the
caller actually said and drops any "yes" whose quote can't be found, so a judge
can't invent evidence or be triggered by the listener's own words.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from .pricing import estimate_tokens
from .signals import Signal
from .transcript import Transcript


@dataclass(frozen=True)
class Answer:
    id: str
    quote: str  # the caller's words, as the judge gave them


@dataclass
class Reply:
    yes: list[Answer]
    input_tokens: int = 0
    output_tokens: int = 0
    note: str = ""  # e.g. why a reply couldn't be parsed
    latency: float | None = None  # seconds the model took, when known (a cached reply keeps the original)


class Judge(Protocol):
    name: str

    def ask(self, questions: Sequence[Signal], transcript: Transcript) -> Reply: ...


# Muse Spark judge prompt v1 (Oct 28, 2026). Drafted before any call to the API.
SPARK_SYSTEM_V1 = """You listen to a phone call in India alongside the person who received it (YOU). You read the transcript so far and answer fixed questions about what the CALLER has said. You never decide whether the call is a scam; you only answer the questions.

- Judge only the CALLER's lines. Read YOU's lines only to understand the caller.
- The transcript may be in Hindi, Marathi, English or a mix, in Devanagari or Latin script, and may contain transcription mistakes.
- A question is "yes" only if the caller has clearly said it, directly or in other words. Whether the caller's claim is true doesn't matter.
- For each "yes", copy the caller's exact words that show it, at most 25 words, into "quote". Keep the original script and spelling; don't translate, correct or join words from different places.
- If the caller hasn't said it yet, leave the question out. Don't guess what the caller will say next.
- A caller saying they will NOT ask for something (for example "we never ask for your OTP") is not asking for it.

Reply with JSON only, listing only the questions answered "yes":
{"yes": [{"id": "A1", "quote": "..."}]}"""

# "Check before you pay": the text is the listener's own account, typed after the call, not the caller's words.
# On Oct 30 the call prompt above answered no to everything on a first-person retelling ("a police officer
# called me… they said I will be arrested"). The evaluation never uses this prompt; only the typed check does.
SPARK_SYSTEM_TYPED_V1 = """Someone in India got a phone call and afterwards wrote down what the CALLER said and did, in their own words (for example "he said…", "they told me…", "a police officer called me"). You answer fixed questions about what the caller said or did, as this account reports it. You never decide whether the call is a scam; you only answer the questions.

- Treat whatever the account says the caller said or did as the caller saying or doing it: "he said my Aadhaar was found in a case" means the caller said that.
- The account may be in Hindi, Marathi, English or a mix, in Devanagari or Latin script.
- A question is "yes" only if the account clearly reports it, directly or in other words. Whether the caller's claim is true doesn't matter.
- For each "yes", copy the account's exact words that show it, at most 25 words, into "quote". Keep the original script and spelling; don't translate, correct or join words from different places.
- If the account doesn't report it, leave the question out. Don't guess what came next.
- A caller saying they will NOT ask for something (for example "we never ask for your OTP") is not asking for it.

Reply with JSON only, listing only the questions answered "yes":
{"yes": [{"id": "A1", "quote": "..."}]}"""

SPARK_SCHEMA_V1 = {
    "type": "object",
    "properties": {
        "yes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "quote": {"type": "string"}},
                "required": ["id", "quote"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["yes"],
    "additionalProperties": False,
}


def spark_user_message(questions: Sequence[Signal], transcript: Transcript) -> str:
    listed = "\n".join(f"{q.id}: {q.question}" for q in questions)
    return f"TRANSCRIPT SO FAR:\n{transcript.dialogue()}\n\nQUESTIONS:\n{listed}"


def parse_spark_reply(text: str, questions: Sequence[Signal]) -> tuple[list[Answer], str]:
    """The "yes" answers in a reply, keeping only known question ids. Never raises."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start = text.find("{")
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:]) if start >= 0 else (None, 0)
    except json.JSONDecodeError:
        obj = None
    if not isinstance(obj, dict) or not isinstance(obj.get("yes"), list):
        return [], "reply was not the expected JSON"
    asked = {q.id for q in questions}
    answers = []
    for item in obj["yes"]:
        if isinstance(item, dict) and item.get("id") in asked and str(item.get("quote", "")).strip():
            answers.append(Answer(item["id"], str(item["quote"]).strip()))
    return answers, ""


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency: float | None = None


Complete = Callable[[str, str, dict], Completion]  # complete(system, user, json_schema)


@dataclass
class SparkSized:
    """Wraps an offline judge and counts the tokens Muse Spark would use for the same questions."""

    inner: Judge
    output_tokens_per_yes: int = 40

    @property
    def name(self) -> str:
        return f"{self.inner.name} (sized as Spark)"

    def ask(self, questions: Sequence[Signal], transcript: Transcript) -> Reply:
        reply = self.inner.ask(questions, transcript)
        n_in = estimate_tokens(SPARK_SYSTEM_V1 + spark_user_message(questions, transcript))
        n_out = 16 + self.output_tokens_per_yes * len(reply.yes)
        return Reply(reply.yes, n_in, n_out, reply.note)


@dataclass
class SparkJudge:
    """Muse Spark answering the questions. The API client is passed in, so this file makes no calls."""

    complete: Complete
    name: str = "muse-spark-1.3"
    system: str = SPARK_SYSTEM_V1
    calls: int = field(default=0, init=False)

    def ask(self, questions: Sequence[Signal], transcript: Transcript) -> Reply:
        self.calls += 1
        done = self.complete(self.system, spark_user_message(questions, transcript), SPARK_SCHEMA_V1)
        answers, note = parse_spark_reply(done.text, questions)
        return Reply(answers, done.input_tokens, done.output_tokens, note, done.latency)


# Comparison B: Muse Spark asked the whole question at once, with no signals and no rules.
FREEFORM_SYSTEM_V1 = """You listen to a phone call in India alongside the person who received it (YOU). The transcript may be in Hindi, Marathi, English or a mix.
Is this call a scam? Answer only from what has been said so far.
Reply with JSON only: {"scam": true or false}"""

FREEFORM_SCHEMA_V1 = {
    "type": "object",
    "properties": {"scam": {"type": "boolean"}},
    "required": ["scam"],
    "additionalProperties": False,
}


# "Check before you pay": the overall view of a typed retelling, as SPARK_SYSTEM_TYPED_V1 is for the signals.
FREEFORM_SYSTEM_TYPED_V1 = """Someone in India got a phone call and afterwards wrote down what the CALLER said and did, in their own words. The account may be in Hindi, Marathi, English or a mix.
Was this call a scam? Answer only from what the account reports.
Reply with JSON only: {"scam": true or false}"""


@dataclass
class FreeFormJudge:
    complete: Complete
    name: str = "muse-spark-1.3 free-form"
    system: str = FREEFORM_SYSTEM_V1

    def ask(self, questions: Sequence[Signal], transcript: Transcript) -> Reply:
        done = self.complete(self.system, f"TRANSCRIPT SO FAR:\n{transcript.dialogue()}", FREEFORM_SCHEMA_V1)
        text = re.sub(r"^```(?:json)?|```$", "", done.text.strip(), flags=re.MULTILINE).strip()
        try:
            scam = json.loads(text[text.find("{"):]).get("scam") is True
        except (json.JSONDecodeError, AttributeError):
            return Reply([], done.input_tokens, done.output_tokens, "reply was not the expected JSON", done.latency)
        yes = [Answer("SCAM", "")] if scam else []
        return Reply(yes, done.input_tokens, done.output_tokens, "", done.latency)


@dataclass
class CheckedJudge:
    """Teesra Kaan's judge since rules v1.3: Muse Spark answers the signal questions (prompt v1) and,
    in a parallel call, gives its overall view of the call (comparison B's prompt). Both prompts are
    unchanged; the rules (signals.decide_checked) need both a "scam" and a quoted signal. Once the
    overall view has said scam it isn't asked again."""

    signs: SparkJudge
    verdict: FreeFormJudge
    name: str = "muse-spark-1.3 checked"

    @property
    def signals(self) -> tuple[Signal, ...]:
        from .signals import SCAM, SIGNALS

        return SIGNALS + (SCAM,)

    @property
    def decide(self):
        from .signals import decide_checked

        return decide_checked

    def ask(self, questions: Sequence[Signal], transcript: Transcript) -> Reply:
        from concurrent.futures import ThreadPoolExecutor

        signs = [q for q in questions if q.id != "SCAM"]
        with ThreadPoolExecutor(2) as pool:
            overall = pool.submit(self.verdict.ask, (), transcript) if len(signs) < len(questions) else None
            a = self.signs.ask(signs, transcript) if signs else Reply([], 0, 0, "", 0.0)
            b = overall.result() if overall else Reply([], 0, 0, "", 0.0)
        latencies = [r.latency for r in (a, b) if r.latency is not None]
        return Reply(a.yes + b.yes, a.input_tokens + b.input_tokens, a.output_tokens + b.output_tokens,
                     "; ".join(n for n in (a.note, b.note) if n), max(latencies) if latencies else None)
