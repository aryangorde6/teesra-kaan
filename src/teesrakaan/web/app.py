"""The listener page's server: a demo call, or the live microphone, through the same Listener the evaluation uses.

Demo calls replay a written call at the speed it was spoken. Live listening relays the
browser's microphone to Muse Voice Transcribe and runs Muse Spark on what it hears; it's
paid, so it's off unless TEESRAKAAN_ALLOW_PAID=1, each session is capped in length, and
everything the page spends counts against its own $5 share of the ledger's $100 stop.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .. import config
from ..asr import REALTIME_URL, handshake
from ..judge import SPARK_SYSTEM_TYPED_V1, SparkJudge
from ..keywords import KeywordJudge
from ..live import LiveCall
from ..messages import COUNTRIES, LANGS, SIGNAL_NAME, prediction_events, script_ahead, warning
from ..playbook import ahead
from ..report import build_report
from ..simulate import Timing, simulate
from ..transcript import CALLER, Call, Turn, load_call

STATIC = Path(__file__).parent / "static"
DEMO_CALLS = Path(os.environ.get("TEESRAKAAN_DEMO_CALLS", Path(__file__).resolve().parents[3] / "examples" / "calls"))
MAX_LIVE_SECONDS = 6 * 60
MAX_LIVE_SESSIONS = 3
WEB_CAP_USD = 5.0  # what the page may spend, of the ledger's $100 stop
_live_sessions = 0

app = FastAPI(title="Teesra Kaan", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
if DEMO_CALLS.is_dir():
    app.mount("/demo-audio", StaticFiles(directory=DEMO_CALLS), name="demo-audio")


AUDIO_SUFFIXES = (".m4a", ".mp3", ".ogg", ".wav")


def _demo_calls() -> dict[str, Call]:
    """Written calls, and re-enacted recordings saved as transcription sessions (the real Muse transcript, replayed
    at the times it arrived, at no cost). A recording's audio sits next to its JSON with the same name."""
    from ..asr import session_to_call

    out = {}
    for path in sorted(DEMO_CALLS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "events" in data:
            out[path.stem] = session_to_call(data, path.stem, set="demo", re_enactment=True, label=data.get("label", {}))
        else:
            out[path.stem] = load_call(path)
    return out


def _audio(call_id: str) -> str | None:
    for suffix in AUDIO_SUFFIXES:
        if (DEMO_CALLS / f"{call_id}{suffix}").is_file():
            return f"/demo-audio/{call_id}{suffix}"
    return None


def demo_judge():
    """The keyword stand-in by default (free). With TEESRAKAAN_DEMO_JUDGE=spark and live listening available,
    Muse Spark: the first play of a call is paid, and replays come from the reply cache at no cost."""
    if config.env("TEESRAKAAN_DEMO_JUDGE") == "spark" and live_available():
        return live_judge()
    return KeywordJudge()


def demo_events(call: Call, lang: str, timing: Timing = Timing(), judge=None,
                country: str = "IN") -> list[tuple[float, dict]]:
    """Everything the page shows for one call, as (seconds into the call, event). `country` is where the
    listener is, which decides where the warning and the report send them."""
    judge = judge or KeywordJudge()
    if any(t.heard_times for t in call.turns):
        timing = Timing(judge_latency=None)  # a recorded session: real transcription times, the judge's own latency
    result = simulate(call, judge, timing)
    events: list[tuple[float, int, dict]] = [(0.0, 0, {
        "type": "start",
        "call": {"id": call.id, "language": call.language, "duration": call.duration,
                 "re_enactment": call.re_enactment, "label": call.label, "audio": _audio(call.id),
                 "judge": "Muse Spark" if judge.name.startswith("muse-spark") else "keyword stand-in (no model)"},
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
                                         "warning": warning(update.alarm, dict(quotes), lang, country)}))
        events.extend((update.t, 3, e) for e in prediction_events(update, lang))
    pack = build_report(call, result.listener, lang, country=country)
    # The report comes last: after the call, and after any answer the judge was still working on when it ended.
    end = max([call.duration + timing.transcribe_delay] + [u.t + 0.1 for u in result.listener.updates])
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


def web_ledger():
    """The ledger, with everything the page spends counted against its own share."""
    from ..budget import Ledger, meta_cap

    return Ledger("meta", meta_cap(), scope="web", scope_cap_usd=WEB_CAP_USD)


def live_available() -> bool:
    """Paid calls allowed, a key set, and a $1 call would pass every spending check (budget.py)."""
    config.load_dotenv()
    if not (config.paid_calls_allowed() and config.env("MODEL_API_KEY")):
        return False
    return web_ledger().refusal(1.0) is None


def live_judge():
    """Muse Spark, unless TEESRAKAAN_LIVE_JUDGE=keywords (no Spark cost: transcription only)."""
    if config.env("TEESRAKAAN_LIVE_JUDGE") == "keywords":
        return KeywordJudge()
    from ..spark import SparkClient

    return SparkJudge(SparkClient(ledger=web_ledger()))


@app.get("/api/signals")
def signals() -> dict:
    """What the page shows under "How it decides": the questions Spark answers, and the rules."""
    from ..signals import RULES_VERSION, SIGNALS

    return {
        "rules_version": RULES_VERSION,
        "signals": [{"id": s.id, "kind": s.kind, "question": s.question, "name": SIGNAL_NAME[s.id]} for s in SIGNALS],
    }


@app.get("/api/calls")
def calls() -> list[dict]:
    return [{"id": c.id, "language": c.language, "duration": c.duration, "re_enactment": c.re_enactment,
             "audio": _audio(c.id)} for c in _demo_calls().values()]


@app.websocket("/ws/demo")
async def demo(ws: WebSocket) -> None:
    await ws.accept()
    call = _demo_calls().get(ws.query_params.get("call", ""))
    lang = ws.query_params.get("lang", "en")
    country = ws.query_params.get("country", "IN")
    try:
        speed = min(max(float(ws.query_params.get("speed", "1")), 0.25), 20.0)
    except ValueError:
        speed = 1.0
    if call is None or lang not in LANGS or country not in COUNTRIES:
        await ws.send_json({"type": "error", "message": "unknown call, language or country"})
        await ws.close()
        return
    clock = 0.0
    try:
        events = await asyncio.to_thread(demo_events, call, lang, Timing(), demo_judge(), country)
        for t, event in events:
            await asyncio.sleep(max(t - clock, 0) / speed)
            clock = max(clock, t)
            await ws.send_json(event)
        await ws.close()
    except WebSocketDisconnect:
        return


MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@app.post("/api/check")
async def check_recording(request: Request) -> dict:
    """A call someone already recorded: batch-transcribed, then the same Listener, warnings and report.
    The audio is converted in memory and never stored."""
    lang = request.query_params.get("lang", "en")
    country = request.query_params.get("country", "IN")
    if lang not in LANGS or country not in COUNTRIES:
        raise HTTPException(400, "Unknown language or country.")
    if not live_available():
        raise HTTPException(503, "Checking recordings is switched off on this server.")
    body = await request.body()
    if not body or len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Send one recording, up to 25 MB and 10 minutes.")
    from ..asr import batch_to_call, transcribe_batch, wav16k

    def run() -> list[dict]:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".audio") as f:
            f.write(body)
            f.flush()
            wav = wav16k(f.name)
        call = batch_to_call(transcribe_batch(wav, ledger=web_ledger()), "your-recording")
        return [{"t": t, **event} for t, event in demo_events(call, lang, Timing(), live_judge(), country)]

    try:
        return {"events": await asyncio.to_thread(run)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


MAX_SAID_CHARS = 2000


def check_said(text: str, lang: str = "en", country: str = "IN", judge=None) -> dict:
    """What a caller said, typed in (or voice-typed) after the call: the same judge, quote check and
    rules, plus the scam it matches and the rest of its script. It runs on the phone that had the call,
    which live listening can't, so it can be checked before anyone pays."""
    judge = judge or KeywordJudge()
    if isinstance(judge, SparkJudge):  # a retelling, not the caller's own words
        judge = dataclasses.replace(judge, system=SPARK_SYSTEM_TYPED_V1)
    call = Call("what-the-caller-said", (Turn(CALLER, 0.0, max(len(text.split()) / 2.5, 1.0), text),), set="typed")
    listener = simulate(call, judge, Timing(check_every=float("inf"))).listener  # one question round, at the end
    found = sorted(listener.found.values(), key=lambda f: f.said_at)
    quotes = {f.id: f.quote for f in found}
    return {
        "judge": "Muse Spark" if judge.name.startswith("muse-spark") else "keyword stand-in (no model)",
        "signals": [{"id": f.id, "name": SIGNAL_NAME[f.id][lang], "quote": f.quote} for f in found],
        "warning": warning(listener.alarm, quotes, lang, country),
        "ahead": script_ahead(ahead(quotes), lang),
        "report_markdown": build_report(call, listener, lang, country=country).to_markdown(),
    }


@app.post("/api/said")
async def said(request: Request) -> dict:
    lang = request.query_params.get("lang", "en")
    country = request.query_params.get("country", "IN")
    if lang not in LANGS or country not in COUNTRIES:
        raise HTTPException(400, "Unknown language or country.")
    try:
        text = str((await request.json()).get("text", "")).strip()
    except (ValueError, AttributeError):
        text = ""
    if not text or len(text) > MAX_SAID_CHARS:
        raise HTTPException(400, f"Write what the caller said, up to {MAX_SAID_CHARS} characters.")
    judge = live_judge() if live_available() else KeywordJudge()
    return await asyncio.to_thread(check_said, text, lang, country, judge)


@app.websocket("/ws/live")
async def live(ws: WebSocket) -> None:
    """Browser audio (16 kHz 16-bit mono PCM, binary frames) in; the same events as a demo call out."""
    global _live_sessions
    await ws.accept()
    lang = ws.query_params.get("lang", "en")
    country = ws.query_params.get("country", "IN")
    if lang not in LANGS or country not in COUNTRIES:
        await ws.send_json({"type": "error", "message": "unknown language or country"})
        await ws.close()
        return
    if not live_available():
        await ws.send_json({"type": "error", "message": "Live listening is switched off on this server."})
        await ws.close()
        return
    if _live_sessions >= MAX_LIVE_SESSIONS:
        await ws.send_json({"type": "error", "message": "Too many people are listening right now. Try a demo call."})
        await ws.close()
        return
    from ..asr import MODEL as ASR_MODEL
    from ..budget import BudgetExceeded, PaidCallsDisabled
    from ..pricing import TRANSCRIBE_PER_HOUR

    ledger = web_ledger()
    try:  # the whole session's worst case, settled to its real length at the end
        call_id = ledger.reserve(ASR_MODEL, MAX_LIVE_SECONDS / 3600 * TRANSCRIBE_PER_HOUR, note="live")
    except (BudgetExceeded, PaidCallsDisabled):
        await ws.send_json({"type": "error", "message": "Live listening is switched off on this server."})
        await ws.close()
        return
    _live_sessions += 1
    settled = False
    from websockets.asyncio.client import connect

    loop = asyncio.get_running_loop()
    opened = loop.time()
    call = LiveCall(live_judge(), lang, country=country)
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
            seconds = min(loop.time() - opened, MAX_LIVE_SECONDS)
            ledger.settle(call_id, seconds / 3600 * TRANSCRIBE_PER_HOUR, request_id=ack["sessionId"])
            settled = True
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
        if not settled:
            ledger.mark_unknown(call_id)  # it may have been billed: keep the worst case as spent
        _live_sessions -= 1
