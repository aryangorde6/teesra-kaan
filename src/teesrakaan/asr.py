"""Muse Voice Transcribe: stream audio in real time, keep every event, and turn the log into a timed call.

A session's events are saved with the second each one arrived, so the judge and
rules can be replayed over the same transcript many times (comparisons, ablations)
while every timing still includes the real transcription delay. Protocol:
dev.meta.ai/docs/speech-to-text (read Oct 28, 2026).
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .transcript import Call, Turn

REALTIME_URL = "wss://api.meta.ai/v1/asr/realtime"
MODEL = "muse-voice-transcribe-1.0"
SAMPLE_RATE = 16_000
BYTES_PER_SECOND = SAMPLE_RATE * 2  # PCM_16KHZ: signed 16-bit little-endian, mono
CHUNK_SECONDS = 0.1  # the page sends 100 ms frames

# Terms the transcriber should expect (keyword biasing). Ablation: run with none.
KEYWORDS = (
    "CBI", "ED", "NCB", "TRAI", "DoT", "RBI", "KYC", "OTP", "UPI", "PIN", "CVV", "Aadhaar", "PAN",
    "FedEx", "DHL", "customs", "crime branch", "cyber cell", "digital arrest", "FIR", "warrant",
    "AnyDesk", "TeamViewer", "Skype", "WhatsApp", "1930",
)
LANGUAGES = ("Hindi", "Marathi", "English")


def handshake(
    key: str,
    mode: str = "DIARIZATION",
    languages: tuple[str, ...] = LANGUAGES,
    keywords: tuple[str, ...] = KEYWORDS,
) -> dict:
    """The first frame. Language bias and keywords are fixed for the session."""
    msg: dict = {
        "authorization": {"accessToken": f"Bearer {key}"},
        "audioEncoding": "PCM_16KHZ",
        "model": MODEL,
        "mode": mode,
        "partialMode": "CUMULATIVE",
        "emitAudioProgress": False,
    }
    if languages:
        msg["languageBias"] = list(languages)
    if keywords:
        msg["keywords"] = list(keywords)
    return msg


def pcm16k(path: str | Path) -> bytes:
    """Any audio file as raw 16 kHz mono 16-bit PCM, by ffmpeg."""
    out = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path),
         "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-acodec", "pcm_s16le", "-"],
        check=True, capture_output=True,
    )
    return out.stdout


@dataclass
class Session:
    session_id: str
    settings: dict  # the handshake without the key
    audio_seconds: float
    events: list[dict]  # every server frame, plus "received": seconds since the first audio was sent

    def to_json(self) -> dict:
        return dict(self.__dict__)


async def stream(pcm: bytes, first_frame: dict, url: str = REALTIME_URL, connect=None) -> Session:
    """Sends `pcm` at real-time pace and collects events until the server closes the stream."""
    if connect is None:
        from websockets.asyncio.client import connect
    chunk = int(BYTES_PER_SECOND * CHUNK_SECONDS)
    events: list[dict] = []
    async with connect(url, max_size=None) as ws:
        await ws.send(json.dumps(first_frame))
        ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        if "sessionId" not in ack:
            raise RuntimeError(f"no session: {ack}")
        started = time.monotonic()

        async def send() -> None:
            for i, start in enumerate(range(0, len(pcm), chunk)):
                await ws.send(pcm[start : start + chunk])
                # Pace to the audio clock, never ahead of real time.
                await asyncio.sleep(max(0.0, started + (i + 1) * CHUNK_SECONDS - time.monotonic()))
            await ws.send(json.dumps({"type": "endStream"}))

        async def receive() -> None:
            async for frame in ws:
                if isinstance(frame, bytes):
                    continue
                event = json.loads(frame)
                event["received"] = round(time.monotonic() - started, 3)
                events.append(event)
                if event.get("type") == "error":
                    raise RuntimeError(f"transcription error: {event.get('message')}")

        await asyncio.gather(send(), receive())
    settings = {k: v for k, v in first_frame.items() if k != "authorization"}
    return Session(ack["sessionId"], settings, len(pcm) / BYTES_PER_SECOND, events)


def session_to_call(session: Session | dict, call_id: str, **meta) -> Call:
    """Turns a session's events into turns, with each word's time said and time heard.

    Partials are cumulative: a word's "heard" time is when it first appeared in one,
    and its "said" time is the server's audio clock at that moment. The final text of
    a turn comes from speechComplete (or the last final transcript).
    """
    events = session.events if isinstance(session, Session) else session["events"]
    turns: dict[str, dict] = {}
    order: list[str] = []
    current = None
    for e in events:
        kind = e.get("type")
        if kind == "speechStart":
            current = str(e.get("turnId"))
            turns[current] = {"start": e.get("audioProcessedMs", 0) / 1000, "end": None, "speaker": "A",
                              "said": [], "heard": [], "text": ""}
            order.append(current)
        elif kind == "transcript" and current is not None:
            turn = turns[current]
            words = (e.get("transcript") or "").split()
            for _ in range(len(turn["heard"]), len(words)):
                turn["said"].append(e.get("audioProcessedMs", 0) / 1000)
                turn["heard"].append(e["received"])
            turn["text"] = " ".join(words)
        elif kind == "speaker" and current is not None:
            turns[current]["speaker"] = str(e.get("label") or "A")
        elif kind == "speechEnd":
            tid = str(e.get("turnId"))
            if tid in turns:
                turns[tid]["end"] = e.get("audioProcessedMs", 0) / 1000
        elif kind == "speechComplete":
            tid = str(e.get("turnId"))
            if tid in turns:
                turn = turns[tid]
                words = (e.get("transcript") or turn["text"]).split()
                while len(turn["heard"]) < len(words):  # words that never showed in a partial
                    turn["said"].append(e.get("audioProcessedMs", 0) / 1000)
                    turn["heard"].append(e["received"])
                turn["text"] = " ".join(words)
                turn["said"], turn["heard"] = turn["said"][: len(words)], turn["heard"][: len(words)]
    out = []
    for tid in order:
        t = turns[tid]
        if not t["text"]:
            continue
        end = t["end"] if t["end"] is not None else max(t["said"], default=t["start"])
        out.append(Turn(t["speaker"], t["start"], max(end, t["start"]), t["text"],
                        word_times=tuple(t["said"]), heard_times=tuple(t["heard"])))
    return Call(id=call_id, turns=tuple(out), **meta)


def transcribe_file(path: str | Path, ledger=None, **settings) -> Session:
    """One recording through the realtime API, paced at real time. Paid ($0.18 per hour), so it
    goes through the same $120 ledger as Spark, and only when TEESRAKAAN_ALLOW_PAID=1."""
    from . import config
    from .budget import Ledger, meta_cap
    from .pricing import TRANSCRIBE_PER_HOUR

    pcm = pcm16k(path)
    cost = len(pcm) / BYTES_PER_SECOND / 3600 * TRANSCRIBE_PER_HOUR
    ledger = ledger or Ledger("meta", meta_cap())
    call_id = ledger.reserve(MODEL, cost, note=Path(path).name)
    try:
        session = asyncio.run(stream(pcm, handshake(config.api_key(), **settings)))
    except Exception:
        ledger.mark_unknown(call_id)
        raise
    ledger.settle(call_id, cost, request_id=session.session_id)
    return session
