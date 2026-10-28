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
    monkeypatch.setenv("TEESRAKAAN_DATA", str(tmp_path))
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
