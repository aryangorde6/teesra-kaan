"""The listener page's server. A demo call is played live through the same Listener the evaluation uses.

Until the speech API is connected, the page's input is a demo call: its words arrive
at the speed they were spoken, and the warnings arrive when the Listener raises them.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..keywords import KeywordJudge
from ..messages import LANGS, SIGNAL_NAME, warning
from ..report import build_report
from ..simulate import Timing, simulate
from ..transcript import Call, load_call

STATIC = Path(__file__).parent / "static"
DEMO_CALLS = Path(os.environ.get("TEESRAKAAN_DEMO_CALLS", Path(__file__).resolve().parents[3] / "examples" / "calls"))

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
    for t, speaker, word in call.words():
        events.append((t + timing.transcribe_delay, 1, {"type": "word", "speaker": speaker, "t": round(t, 2), "word": word}))
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

