import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from teesrakaan.web.app import MAX_LIVE_SECONDS, app, demo_events  # noqa: E402

client = TestClient(app)


def test_page_and_call_list():
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    ids = {c["id"] for c in client.get("/api/calls").json()}
    assert {"demo-digital-arrest", "demo-trai-marathi", "demo-bank-alert-genuine"} <= ids


def test_demo_events_tell_the_whole_story_in_order(example):
    events = demo_events(example("demo-digital-arrest"), "mr")
    kinds = [e["type"] for _, e in events]
    assert kinds[0] == "start" and kinds[-1] == "end"
    assert [t for t, _ in events] == sorted(t for t, _ in events)
    alarms = [e for _, e in events if e["type"] == "alarm"]
    assert [a["warning"]["level"] for a in alarms] == ["amber", "red"]
    assert alarms[-1]["warning"]["headline"].startswith("धोका")
    end = events[-1][1]
    assert end["timing"]["t_warn"] < end["timing"]["t_ask"]
    assert "1930" in end["report_markdown"]


def test_unknown_call_gets_an_error():
    with client.websocket_connect("/ws/demo?call=nope&lang=en") as ws:
        assert ws.receive_json()["type"] == "error"


def test_a_demo_call_reports_to_the_country_the_page_asks_for():
    with client.websocket_connect("/ws/demo?call=demo-trai-marathi&lang=en&country=US&speed=20") as ws:
        events = []
        while not events or events[-1]["type"] != "end":
            events.append(ws.receive_json())
    assert "ReportFraud.ftc.gov" in events[-1]["report_markdown"]
    red = [e for e in events if e["type"] == "alarm" and e["warning"]["level"] == "red"]
    assert red and "ReportFraud.ftc.gov" in red[0]["warning"]["action"]
    with client.websocket_connect("/ws/demo?call=demo-trai-marathi&lang=en&country=XX") as ws:
        assert ws.receive_json()["type"] == "error"


def _fake_transcriber():
    """A local stand-in for the realtime API, replaying the diarized events from test_asr_and_spark."""
    import json
    import threading

    from websockets.sync.server import serve
    from test_asr_and_spark import SCRIPT

    def handler(ws):
        first = json.loads(ws.recv())
        assert first["audioEncoding"] == "PCM_16KHZ"
        ws.send(json.dumps({"sessionId": "live-1"}))
        sent = False
        for frame in ws:
            if isinstance(frame, bytes) and not sent:
                for event in SCRIPT:
                    ws.send(json.dumps(event))
                sent = True
            elif isinstance(frame, str) and json.loads(frame).get("type") == "endStream":
                ws.close()
                return

    server = serve(handler, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_live_is_off_without_permission():
    assert client.get("/api/status").json() == {"live": False}
    with client.websocket_connect("/ws/live?lang=en") as ws:
        assert ws.receive_json()["type"] == "error"


def test_live_listening_end_to_end_with_a_fake_transcriber(monkeypatch, tmp_path):
    server = _fake_transcriber()
    port = server.socket.getsockname()[1]
    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("TEESRAKAAN_LIVE_JUDGE", "keywords")
    monkeypatch.setenv("TEESRAKAAN_ASR_URL", f"ws://127.0.0.1:{port}")
    from teesrakaan.budget import Ledger

    Ledger("meta", 100.0).record_meter(150.0, 0.0, "test")
    try:
        with client.websocket_connect("/ws/live?lang=hi") as ws:
            assert ws.receive_json()["type"] == "start"
            ws.send_bytes(b"\0" * 3200)
            events = []
            while not any(e["type"] == "word" and e["word"] == "batana." for e in events):
                events.append(ws.receive_json())
            ws.send_text('{"type": "stop"}')
            while events[-1]["type"] != "end":
                events.append(ws.receive_json())
    finally:
        server.shutdown()
    words = [e for e in events if e["type"] == "word"]
    assert words[0]["word"] == "Hello?" and words[-1]["word"] == "batana."
    assert {e["speaker"] for e in words if e["word"] == "FIR"} == {"caller"}
    alarms = [e["warning"]["level"] for e in events if e["type"] == "alarm"]
    assert alarms and alarms[-1] == "red"
    assert "1930" in events[-1]["report_markdown"]
    spent = Ledger("meta", 100.0).summary()  # the session's transcription is in the ledger, at its real length
    assert spent.calls == 1 and spent.reserved_usd == 0 and 0 < spent.spent_usd < MAX_LIVE_SECONDS / 3600 * 0.18


def test_live_switches_itself_off_when_the_budget_is_spent(monkeypatch):
    from teesrakaan.budget import Ledger

    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("TEESRAKAAN_BUDGET_META_USD", "5")
    ledger = Ledger("meta", 5.0)
    assert client.get("/api/status").json() == {"live": False}  # Meta's meter not read yet
    ledger.record_meter(150.0, 0.0, "test")
    assert client.get("/api/status").json() == {"live": True}
    ledger.settle(ledger.reserve("muse-spark-1.3", 4.5), 4.5)
    assert client.get("/api/status").json() == {"live": False}


def test_signals_endpoint_lists_the_thirteen_questions():
    data = client.get("/api/signals").json()
    assert len(data["signals"]) == 13 and data["rules_version"].startswith("v1.3")
    assert {"en", "hi", "mr"} <= data["signals"][0]["name"].keys()


def test_a_recorded_session_is_a_demo_call_with_its_audio(tmp_path, monkeypatch):
    import json

    from teesrakaan.web import app as web
    from test_asr_and_spark import SCRIPT

    events = [dict(e, received=0.3 * i + 0.5) for i, e in enumerate(SCRIPT)]
    (tmp_path / "IS-demo.json").write_text(json.dumps({"session_id": "s", "settings": {}, "audio_seconds": 3, "events": events}))
    (tmp_path / "IS-demo.m4a").write_bytes(b"\0")
    monkeypatch.setattr(web, "DEMO_CALLS", tmp_path)
    listed = client.get("/api/calls").json()
    assert listed == [{"id": "IS-demo", "language": "", "duration": listed[0]["duration"], "re_enactment": True,
                       "audio": "/demo-audio/IS-demo.m4a"}]
    out = web.demo_events(web._demo_calls()["IS-demo"], "en")
    assert out[0][1]["call"]["judge"] == "keyword stand-in (no model)"
    assert any(e["type"] == "alarm" and e["warning"]["level"] == "red" for _, e in out)


def test_checking_a_recording_end_to_end(monkeypatch):
    import teesrakaan.asr as asr

    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("TEESRAKAAN_LIVE_JUDGE", "keywords")
    monkeypatch.setattr(asr, "wav16k", lambda path: b"wav")
    from teesrakaan.budget import Ledger

    Ledger("meta", 100.0).record_meter(150.0, 0.0, "test")
    monkeypatch.setattr(asr, "transcribe_batch", lambda wav, ledger=None: {"turns": [
        {"startMs": 0, "endMs": 1200, "transcript": "Haan ji?", "speaker": "A"},
        {"startMs": 1500, "endMs": 9000, "speaker": "B",
         "transcript": "Main TRAI se bol raha hoon. Aapka number do ghante mein band ho jayega. OTP bata dijiye."}]})
    assert client.post("/api/check?lang=mr", content=b"#EXTM3U\nfile:///etc/passwd").status_code == 400  # never reaches ffmpeg
    r = client.post("/api/check?lang=mr", content=b"RIFF\x24\x00\x00\x00WAVEfmt ")
    assert r.status_code == 200
    events = r.json()["events"]
    assert events[0]["type"] == "start" and events[-1]["type"] == "end"
    assert any(e["type"] == "alarm" and e["warning"]["level"] == "red" for e in events)
    assert "1930" in events[-1]["report_markdown"]


def test_a_call_typed_in_afterwards_gets_its_scam_and_the_rest_of_the_script(monkeypatch):
    import teesrakaan.web.app as web

    monkeypatch.setattr(web, "live_available", lambda: False)  # the free keyword stand-in, never a paid call
    text = "Main CBI se bol raha hoon. Aapke Aadhaar pe FIR darj hai. Skype pe video call pe aaiye."
    r = client.post("/api/said?lang=hi", json={"text": text})
    assert r.status_code == 200
    data = r.json()
    assert [s["id"] for s in data["signals"]] == ["A1", "A2", "A8"]
    assert data["warning"]["level"] == "amber" and "CBI" in data["warning"]["family"]
    assert [s["id"] for s in data["ahead"]["steps"]] == ["A4", "A6"]
    assert "1930" in data["report_markdown"] and "आपने जो लिखा" in data["report_text"] and "**" not in data["report_text"]
    one = client.post("/api/said?lang=en", json={"text": "A man said my parcel was seized."}).json()
    assert one["warning"] is None and not one["ahead"]["steps"] and one["ahead"]["note"]


def test_a_typed_call_must_be_some_text_and_not_too_long():
    assert client.post("/api/said?lang=en", json={"text": "  "}).status_code == 400
    assert client.post("/api/said?lang=en", json={"text": "x" * 2001}).status_code == 400
    assert client.post("/api/said?lang=xx", json={"text": "hello"}).status_code == 400
    assert client.post("/api/said?lang=en", content=b"not json").status_code == 400


def test_live_call_loses_no_word_while_the_judge_runs():
    import threading

    from teesrakaan.keywords import KeywordJudge
    from teesrakaan.live import LiveCall

    call = LiveCall(KeywordJudge())
    call.on_event({"type": "speechStart", "turnId": 1, "audioProcessedMs": 0})
    words = [f"w{i}" for i in range(3000)]
    stop = threading.Event()

    def judge_loop():
        while not stop.is_set():
            call.check(1.0)

    worker = threading.Thread(target=judge_loop)
    worker.start()
    call.on_event({"type": "speechComplete", "turnId": 1, "transcript": " ".join(words), "audioProcessedMs": 9000})
    stop.set()
    worker.join()
    call.check(2.0)
    assert call.listener.transcript.n_words == 3000



def test_live_words_wait_for_their_speaker():
    """On speaker, your own "should I transfer the money?" must never be quoted as the caller's."""
    from teesrakaan.keywords import KeywordJudge
    from teesrakaan.live import LiveCall

    call = LiveCall(KeywordJudge(), min_new_words=1, check_every=0)
    scammer = "Main CBI se bol raha hoon. Aapke naam pe FIR darj hai. Kisi ko mat batana."
    out = []
    for tid, label, text in [(0, "A", scammer), (1, "B", "Kya main paise transfer karun?"), (2, "A", scammer)]:
        call.on_event({"type": "speechStart", "turnId": tid})
        for _ in range(2):  # the same partial twice: the old code took its words as stable, under "A"
            shown = call.on_event({"type": "transcript", "transcript": text, "audioProcessedMs": 1000 * tid + 500})
        assert not [e for e in shown if e["type"] == "word"] and shown[-1]["text"] == text
        assert not call.pending
        out += call.on_event({"type": "speaker", "label": label, "audioProcessedMs": 1000 * tid + 900})
        call.on_event({"type": "speechComplete", "turnId": tid, "transcript": text})
        out += call.check(float(tid + 1))
    lines = call.listener.transcript.lines
    assert [line.speaker for line in lines] == ["A", "B", "A"]
    quotes = " ".join(e["quote"] for e in out if e["type"] == "signal")
    assert quotes and "paise transfer" not in quotes
    assert [e["t"] for e in out if e["type"] == "word"][:2] == [0.5, 0.5]

def test_a_typed_retelling_is_judged_as_one_with_spark():
    """Spark reads typed text as the listener's account; the evaluation's call prompts stay as they were."""
    from teesrakaan.judge import (FREEFORM_SYSTEM_TYPED_V1, FREEFORM_SYSTEM_V1, SPARK_SYSTEM_TYPED_V1,
                                  SPARK_SYSTEM_V1, CheckedJudge, Completion, FreeFormJudge, SparkJudge)
    from teesrakaan.web.app import check_said

    systems = []

    def complete(system, user, schema):
        systems.append(system)
        if system == FREEFORM_SYSTEM_TYPED_V1:
            return Completion('{"scam": true}', 300, 5, 0.5)
        return Completion('{"yes": [{"id": "A1", "quote": "Mumbai Police officer called me"}]}', 900, 40, 1.0)

    judge = CheckedJudge(SparkJudge(complete), FreeFormJudge(complete))
    out = check_said("A Mumbai Police officer called me on WhatsApp.", "en", "IN", judge)
    assert sorted(systems) == sorted([SPARK_SYSTEM_TYPED_V1, FREEFORM_SYSTEM_TYPED_V1])
    assert judge.signs.system == SPARK_SYSTEM_V1 and judge.verdict.system == FREEFORM_SYSTEM_V1
    assert out["judge"] == "Muse Spark" and [s["id"] for s in out["signals"]] == ["A1"]
    assert out["warning"]["level"] == "amber"  # Spark says scam, and one signal is quoted


def test_demo_calls_replay_muse_sparks_saved_replies_without_a_key(example, monkeypatch):
    """The hosted page has no key: its demo calls play Spark's real replies, saved in the repo, in every language."""
    import teesrakaan.web.app as web
    from teesrakaan.spark import ReplayClient

    monkeypatch.delenv("TEESRAKAAN_DEMO_JUDGE", raising=False)
    judge = web.demo_judge()
    assert isinstance(judge.signs.complete, ReplayClient)
    for lang in ("en", "hi", "mr"):
        for name, level in [("demo-digital-arrest", "red"), ("demo-trai-marathi", "red"), ("demo-bank-alert-genuine", None)]:
            events = [e for _, e in web.demo_events(example(name), lang, judge=web.demo_judge())]
            assert events[0]["call"]["judge"] == "Muse Spark"
            levels = [e["warning"]["level"] for e in events if e["type"] == "alarm"]
            assert (levels[-1] if levels else None) == level, (name, lang)


def test_a_demo_call_without_saved_replies_falls_back_to_keywords(example, tmp_path, monkeypatch):
    import teesrakaan.web.app as web

    monkeypatch.setattr(web, "DEMO_REPLIES", tmp_path)
    events = web.demo_events_or_keywords(example("demo-digital-arrest"), "en", "IN")
    assert events[0][1]["call"]["judge"] == "keyword stand-in (no model)"


def test_try_an_example_replays_muse_spark_without_a_key():
    from teesrakaan.web.app import example_texts

    for lang, text in example_texts().items():
        out = client.post(f"/api/said?lang={lang}", json={"text": text}).json()
        assert out["judge"] == "Muse Spark" and out["warning"]["level"] == "red", lang
    out = client.post("/api/said?lang=en", json={"text": "He said he is from the CBI and I must not tell anyone."}).json()
    assert out["judge"] == "keyword stand-in (no model)"  # no saved reply for other text


def test_the_page_plays_only_lines_recorded_for_todays_words():
    from teesrakaan import config, voice
    from teesrakaan.messages import voice_lines

    assert client.get("/api/voice").json() == {}
    config.voice_dir().mkdir(parents=True)
    for line_id, words in (("W-red-IN-mr", voice_lines()["W-red-IN-mr"]["lines"]), ("W-amber-hi", ["old words"])):
        voice.audio_path(line_id).write_bytes(b"m4a")
        voice.meta_path(line_id).write_text(json.dumps({"lines": words}), encoding="utf-8")
    assert list(client.get("/api/voice").json()) == ["W-red-IN-mr"]
    r = client.get("/voice/W-red-IN-mr.m4a")
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mp4"
    assert client.get("/voice/W-red-IN-mr.json").status_code == 404  # the words file isn't served
    assert client.get("/voice/..%2Fsecret.m4a").status_code == 404


def test_the_page_is_revalidated_so_returning_visitors_get_the_current_files():
    r = client.get("/")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
    assert "/static/app.js?v=" in r.text and "/static/style.css?v=" in r.text


def test_every_package_the_code_imports_is_declared():
    # The server installs only what pyproject declares; on Oct 30 the demos crashed there for want of httpx.
    import ast
    import sys
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    declared = {spec.split(">")[0].split("=")[0].split("[")[0].strip().lower()
                for spec in project["dependencies"] + [d for extra in project["optional-dependencies"].values() for d in extra]}
    imported = set()
    for path in (root / "src" / "teesrakaan").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
    third_party = imported - set(sys.stdlib_module_names) - {"teesrakaan", "__future__"}
    assert third_party <= declared, f"imported but not in pyproject.toml: {sorted(third_party - declared)}"


def test_live_shows_gujarati_letters_in_devanagari():
    """A real Marathi voice sometimes comes back in Gujarati letters (dev-log, Oct 31)."""
    from teesrakaan.keywords import KeywordJudge
    from teesrakaan.live import LiveCall

    call = LiveCall(KeywordJudge())
    call.on_event({"type": "speechStart", "turnId": 0})
    shown = call.on_event({"type": "transcript", "transcript": "તુમચે ખાતે", "audioProcessedMs": 900})
    assert shown[-1]["text"] == "तुमचे खाते"
    out = call.on_event({"type": "speaker", "label": "A", "audioProcessedMs": 1000})
    assert [e["word"] for e in out if e["type"] == "word"] == ["तुमचे", "खाते"]


def test_the_page_sets_its_security_headers_and_lists_no_api():
    r = client.get("/")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert "microphone=(self)" in r.headers["permissions-policy"]
    assert client.get("/static/app.js").headers["x-content-type-options"] == "nosniff"
    assert client.get("/openapi.json").status_code == 404


def test_another_site_cant_open_the_sockets():
    from starlette.websockets import WebSocketDisconnect

    for path in ("/ws/demo?call=demo-trai-marathi&lang=en&speed=20", "/ws/live?lang=en"):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(path, headers={"origin": "https://elsewhere.example"}):
                pass
    with client.websocket_connect("/ws/demo?call=demo-trai-marathi&lang=en&speed=20",
                                  headers={"origin": "http://testserver"}) as ws:
        assert ws.receive_json()["type"] == "start"


def test_one_address_is_limited_and_a_huge_body_is_refused(monkeypatch):
    import teesrakaan.web.app as web

    monkeypatch.setattr(web, "live_available", lambda: False)
    monkeypatch.setattr(web, "SAID_LIMIT", web.RateLimit(2))
    assert [client.post("/api/said?lang=en", json={"text": "hello"}).status_code for _ in range(3)] == [200, 200, 429]
    monkeypatch.setattr(web, "SAID_LIMIT", web.RateLimit(2))
    assert client.post("/api/said?lang=en", content=b"x" * 40_000).status_code == 413
    monkeypatch.setattr(web, "DEMO_LIMIT", web.RateLimit(0))
    with client.websocket_connect("/ws/demo?call=demo-trai-marathi&lang=en&speed=20") as ws:
        assert ws.receive_json() == {"type": "error", "message": web.TOO_MANY}


def test_a_rate_limit_forgets_after_its_minute(monkeypatch):
    import teesrakaan.web.app as web

    now = [100.0]
    monkeypatch.setattr(web.time, "monotonic", lambda: now[0])
    limit = web.RateLimit(1)
    assert limit.allow("a") and not limit.allow("a") and limit.allow("b")
    now[0] += 61
    assert limit.allow("a")


def test_only_recordings_reach_ffmpeg():
    from teesrakaan.web.app import is_recording

    for head in (b"RIFF\0\0\0\0WAVE", b"ID3\4", b"\xff\xfb\x90", b"OggS", b"\x1aE\xdf\xa3", b"#!AMR\n", b"\0\0\0\x18ftypM4A "):
        assert is_recording(head), head
    for head in (b"#EXTM3U\n", b"ffconcat version 1.0", b"<html>", b"", b"\xff"):
        assert not is_recording(head), head


def test_the_server_installs_pinned_versions_of_everything_it_needs():
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    pinned = {line.split("==")[0].lower().replace("_", "-") for line in (root / "deploy" / "constraints.txt").read_text().splitlines()
              if "==" in line and not line.startswith("#")}
    web = tomllib.loads((root / "pyproject.toml").read_text())["project"]["optional-dependencies"]["web"]
    assert {spec.split(">")[0].lower() for spec in web} <= pinned
    assert "-c deploy/constraints.txt" in (root / "deploy" / "push.sh").read_text()
