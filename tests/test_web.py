import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from teesrakaan.web.app import app, demo_events  # noqa: E402

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


def test_live_switches_itself_off_when_the_budget_is_spent(monkeypatch):
    from teesrakaan.budget import Ledger

    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("TEESRAKAAN_BUDGET_META_USD", "5")
    assert client.get("/api/status").json() == {"live": True}
    ledger = Ledger("meta", 5.0)
    ledger.settle(ledger.reserve("muse-spark-1.3", 4.5), 4.5)
    assert client.get("/api/status").json() == {"live": False}


def test_signals_endpoint_lists_the_twelve_questions():
    data = client.get("/api/signals").json()
    assert len(data["signals"]) == 12 and data["rules_version"].startswith("v1.2")
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
    monkeypatch.setattr(asr, "transcribe_batch", lambda wav: {"turns": [
        {"startMs": 0, "endMs": 1200, "transcript": "Haan ji?", "speaker": "A"},
        {"startMs": 1500, "endMs": 9000, "speaker": "B",
         "transcript": "Main TRAI se bol raha hoon. Aapka number do ghante mein band ho jayega. OTP bata dijiye."}]})
    r = client.post("/api/check?lang=mr", content=b"fake audio")
    assert r.status_code == 200
    events = r.json()["events"]
    assert events[0]["type"] == "start" and events[-1]["type"] == "end"
    assert any(e["type"] == "alarm" and e["warning"]["level"] == "red" for e in events)
    assert "1930" in events[-1]["report_markdown"]


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
