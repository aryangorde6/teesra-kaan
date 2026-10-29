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

        # The server closes the stream once it has flushed; if it stalls instead, give up after the audio + 60 s.
        await asyncio.wait_for(asyncio.gather(send(), receive()), timeout=len(pcm) / BYTES_PER_SECOND + 60)
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
            # A label covers the text since the previous speechStart or speaker event; a turn is taken as one voice.
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
    goes through the same $100 ledger as Spark, and only when TEESRAKAAN_ALLOW_PAID=1."""
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


AUDIO_SUFFIXES = {".wav", ".m4a", ".mp3", ".ogg", ".opus", ".aac", ".amr", ".3gp", ".flac"}


async def transcribe_many(audio_dir: Path, out_dir: Path, parallel: int = 8, log=print, **settings) -> int:
    """Every recording in `audio_dir`, `parallel` streams at a time; sessions saved as JSON. Resumable."""
    from . import config
    from .budget import Ledger, meta_cap
    from .pricing import TRANSCRIBE_PER_HOUR

    ledger = Ledger("meta", meta_cap())
    key = config.api_key()
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [p for p in sorted(audio_dir.iterdir())
            if p.suffix.lower() in AUDIO_SUFFIXES and not (out_dir / f"{p.stem}.json").exists()]
    gate = asyncio.Semaphore(parallel)

    async def one(path: Path) -> None:
        async with gate:
            pcm = await asyncio.to_thread(pcm16k, path)
            cost = len(pcm) / BYTES_PER_SECOND / 3600 * TRANSCRIBE_PER_HOUR
            call_id = ledger.reserve(MODEL, cost, note=path.name)
            try:
                session = await stream(pcm, handshake(key, **settings))
            except Exception:
                ledger.mark_unknown(call_id)
                raise
            ledger.settle(call_id, cost, request_id=session.session_id)
            (out_dir / f"{path.stem}.json").write_text(
                json.dumps(session.to_json(), ensure_ascii=False, indent=1), encoding="utf-8")
            log(f"{path.name}: {session.audio_seconds:.0f} s, {len(session.events)} events")

    results = await asyncio.gather(*(one(p) for p in todo), return_exceptions=True)
    for path, result in zip(todo, results):
        if isinstance(result, Exception):
            log(f"{path.name}: FAILED {result}")
    return sum(not isinstance(r, Exception) for r in results)


BATCH_URL = "https://api.meta.ai/v1/asr/transcribe"
MAX_BATCH_SECONDS = 10 * 60  # the API refuses longer files


def wav16k(path: str | Path) -> bytes:
    """Any audio file as a 16 kHz mono 16-bit WAV, by ffmpeg, for the batch endpoint."""
    out = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE),
         "-c:a", "pcm_s16le", "-map_metadata", "-1", "-f", "wav", "-"],
        check=True, capture_output=True,
    )
    return out.stdout


def transcribe_batch(wav: bytes, ledger=None, http=None, **settings) -> dict:
    """One recorded call through the batch endpoint (no real-time pacing). Paid, through the $100 ledger."""
    import httpx

    from . import config
    from .budget import Ledger, meta_cap
    from .pricing import TRANSCRIBE_PER_HOUR

    seconds = max(len(wav) - 44, 0) / BYTES_PER_SECOND
    if seconds > MAX_BATCH_SECONDS:
        raise ValueError("recordings longer than 10 minutes aren't accepted")
    request = {k: v for k, v in handshake("", **settings).items() if k != "authorization"}
    ledger = ledger or Ledger("meta", meta_cap())
    call_id = ledger.reserve(MODEL, seconds / 3600 * TRANSCRIBE_PER_HOUR, note="batch")
    http = http or httpx.Client(timeout=120)
    try:
        response = http.post(
            BATCH_URL,
            headers={"Authorization": f"Bearer {config.api_key()}", "Accept": "application/json"},
            files={"request": (None, json.dumps(request), "application/json"), "audio": ("call.wav", wav, "audio/wav")},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code >= 500:
            ledger.mark_unknown(call_id)
        else:
            ledger.release(call_id)  # failed before a transcript, or a 429: not billed
        raise
    except httpx.HTTPError:
        ledger.mark_unknown(call_id)
        raise
    data = response.json()
    ledger.settle(call_id, data.get("audioDurationMs", seconds * 1000) / 3_600_000 * TRANSCRIBE_PER_HOUR,
                  request_id=data.get("sessionId"))
    return data


def batch_to_call(data: dict, call_id: str) -> Call:
    """The batch response's turns (start, end, speaker) as a call; words are spread over each turn."""
    turns = tuple(
        Turn(str(t.get("speaker") or "A"), t.get("startMs", 0) / 1000, t.get("endMs", 0) / 1000, t.get("transcript", ""))
        for t in data.get("turns", []) if (t.get("transcript") or "").strip()
    )
    if not turns and (data.get("transcript") or "").strip():
        turns = (Turn("A", 0.0, data.get("audioDurationMs", 0) / 1000, data["transcript"]),)
    return Call(call_id, turns)
