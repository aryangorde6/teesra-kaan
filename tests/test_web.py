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
