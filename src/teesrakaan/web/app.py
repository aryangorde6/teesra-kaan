"""The listener page's server: a demo call, or the live microphone, through the same Listener the evaluation uses.

Demo calls replay a written call at the speed it was spoken. Live listening relays the
browser's microphone to Muse Voice Transcribe and runs Muse Spark on what it hears; it's
paid, so it's off unless TEESRAKAAN_ALLOW_PAID=1, and each session is capped in length.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .. import config
from ..asr import REALTIME_URL, handshake
from ..judge import SparkJudge
from ..keywords import KeywordJudge
from ..live import LiveCall
from ..messages import LANGS, SIGNAL_NAME, warning
from ..report import build_report
from ..simulate import Timing, simulate
from ..transcript import Call, load_call

STATIC = Path(__file__).parent / "static"
DEMO_CALLS = Path(os.environ.get("TEESRAKAAN_DEMO_CALLS", Path(__file__).resolve().parents[3] / "examples" / "calls"))
MAX_LIVE_SECONDS = 6 * 60
MAX_LIVE_SESSIONS = 3
_live_sessions = 0

app = FastAPI(title="Teesra Kaan", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _demo_calls() -> dict[str, Call]:
    return {c.id: c for c in (load_call(p) for p in sorted(DEMO_CALLS.glob("*.json")))}


def demo_events(call: Call, lang: str, timing: Timing = Timing()) -> list[tuple[float, dict]]:
    """Everything the page shows for one call, as (seconds into the call, event)."""
    result = simulate(call, KeywordJudge(), timing)
    events: list[tuple[float, int, dict]] = [(0.0, 0, {
        "type": "start",
        "call": {"id": call.id, "language": call.language, "duration": call.duration,
                 "re_enactment": call.re_enactment, "label": call.label},
    })]
    caller = call.caller_label()
    for heard, said, speaker, word in call.timed_words(timing.transcribe_delay):
        who = "caller" if speaker == caller else "listener"
        events.append((heard, 1, {"type": "word", "speaker": who, "t": round(said, 2), "word": word}))
    quotes: dict[str, str] = {}
    for update in result.listener.updates:
        for f in update.new:
            quotes[f.id] = f.quote
            events.append((update.t, 2, {"type": "signal", "id": f.id, "name": SIGNAL_NAME[f.id][lang],
                                         "quote": f.quote, "said_at": round(f.said_at, 1)}))
        if update.raised:
            events.append((update.t, 3, {"type": "alarm", "t": round(update.t, 1),
                                         "warning": warning(update.alarm, dict(quotes), lang)}))
    pack = build_report(call, result.listener, lang)
    end = call.duration + timing.transcribe_delay
    events.append((end, 4, {
        "type": "end",
        "timing": {"t_warn": result.t_warn, "t_red": result.t_red,
                   "t0": call.label.get("t0"), "t_ask": call.label.get("t_ask")},
        "report": pack.to_dict(),
        "report_markdown": pack.to_markdown(),
    }))
    events.sort(key=lambda e: (e[0], e[1]))
    return [(t, e) for t, _, e in events]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/api/status")
def status() -> dict:
    return {"live": live_available()}


def live_available() -> bool:
    """Paid calls allowed, a key set, and more than $1 left under this server's stop."""
    config.load_dotenv()
    if not (config.paid_calls_allowed() and config.env("MODEL_API_KEY")):
        return False
    from ..budget import Ledger, meta_cap

    return Ledger("meta", meta_cap()).summary().remaining_usd > 1.0


def live_judge():
    """Muse Spark, unless TEESRAKAAN_LIVE_JUDGE=keywords (no Spark cost: transcription only)."""
    if config.env("TEESRAKAAN_LIVE_JUDGE") == "keywords":
        return KeywordJudge()
    from ..spark import SparkClient

    return SparkJudge(SparkClient())


@app.get("/api/calls")
def calls() -> list[dict]:
    return [{"id": c.id, "language": c.language, "duration": c.duration, "re_enactment": c.re_enactment}
            for c in _demo_calls().values()]


@app.websocket("/ws/demo")
async def demo(ws: WebSocket) -> None:
    await ws.accept()
    call = _demo_calls().get(ws.query_params.get("call", ""))
    lang = ws.query_params.get("lang", "en")
    try:
        speed = min(max(float(ws.query_params.get("speed", "1")), 0.25), 20.0)
    except ValueError:
        speed = 1.0
    if call is None or lang not in LANGS:
        await ws.send_json({"type": "error", "message": "unknown call or language"})
        await ws.close()
        return
    clock = 0.0
    try:
        for t, event in demo_events(call, lang):
            await asyncio.sleep(max(t - clock, 0) / speed)
            clock = max(clock, t)
            await ws.send_json(event)
        await ws.close()
    except WebSocketDisconnect:
        return


@app.websocket("/ws/live")
async def live(ws: WebSocket) -> None:
    """Browser audio (16 kHz 16-bit mono PCM, binary frames) in; the same events as a demo call out."""
    global _live_sessions
    await ws.accept()
    lang = ws.query_params.get("lang", "en")
    if lang not in LANGS or not live_available():
        await ws.send_json({"type": "error", "message": "Live listening is switched off on this server."})
        await ws.close()
        return
    if _live_sessions >= MAX_LIVE_SESSIONS:
        await ws.send_json({"type": "error", "message": "Too many people are listening right now. Try a demo call."})
        await ws.close()
        return
    _live_sessions += 1
    from websockets.asyncio.client import connect

    loop = asyncio.get_running_loop()
    call = LiveCall(live_judge(), lang)
    send_lock = asyncio.Lock()

    async def send(events: list[dict]) -> None:
        async with send_lock:
            for event in events:
                await ws.send_json(event)

    try:
        async with connect(config.env("TEESRAKAAN_ASR_URL") or REALTIME_URL, max_size=None) as asr:
            await asr.send(json.dumps(handshake(config.api_key())))
            ack = json.loads(await asyncio.wait_for(asr.recv(), timeout=10))
            if "sessionId" not in ack:
                raise RuntimeError("the transcriber refused the session")
            started = loop.time()
            await send([{"type": "start", "call": {"id": "live", "language": lang, "duration": MAX_LIVE_SECONDS,
                                                    "re_enactment": False, "label": {}}}])
            checking: asyncio.Task | None = None

            async def run_check(now: float) -> None:
                await send(await asyncio.to_thread(call.check, now))

            async def audio_in() -> None:
                while loop.time() - started < MAX_LIVE_SECONDS:
                    message = await ws.receive()
                    if message["type"] == "websocket.disconnect":
                        break
                    if message.get("bytes"):
                        await asr.send(message["bytes"])
                    elif message.get("text") and json.loads(message["text"]).get("type") == "stop":
                        break
                await asr.send(json.dumps({"type": "endStream"}))

            async def events_out() -> None:
                nonlocal checking
                async for frame in asr:
                    if isinstance(frame, bytes):
                        continue
                    event = json.loads(frame)
                    if event.get("type") == "error":
                        await send([{"type": "error", "message": "The transcriber stopped: " + str(event.get("message"))}])
                        break
                    await send(call.on_event(event))
                    now = loop.time() - started
                    if (checking is None or checking.done()) and call.due(now):
                        checking = asyncio.create_task(run_check(now))

            await asyncio.gather(audio_in(), events_out())
            if checking is not None:
                await checking
            await send(await asyncio.to_thread(call.end, loop.time() - started))
            await ws.close()
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # the page shows why listening stopped
        try:
            await ws.send_json({"type": "error", "message": f"Listening stopped: {exc}"})
            await ws.close()
        except Exception:
            pass
    finally:
        _live_sessions -= 1
