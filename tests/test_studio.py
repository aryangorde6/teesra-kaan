import csv
import io
import wave

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from teesrakaan.labels import read_labels  # noqa: E402
from teesrakaan.web.studio import app, labels_path, recordings_dir  # noqa: E402

client = TestClient(app, client=("127.0.0.1", 50000))
CONSENT = "?voices=AG,PG&consent=1"


def wav(seconds: float = 3.0, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x10\x00" * int(seconds * rate))
    return buf.getvalue()


def test_only_this_laptop_can_open_it():
    outside = TestClient(app, client=("192.168.1.20", 50000))
    assert outside.get("/").status_code == 403
    assert outside.get("/api/cards").status_code == 403
    assert client.get("/").status_code == 200
    assert client.get("/static/studio.js").status_code == 200


def test_cards_come_dev_first_from_the_fixed_split():
    cards = client.get("/api/cards").json()
    assert len(cards) == 70
    splits = [c["split"] for c in cards]
    assert splits == ["dev"] * 28 + ["test"] * 42
    is04 = next(c for c in cards if c["id"] == "IS04")
    assert is04["is_scam"] and is04["pattern"] == 2 and is04["lines"] and not is04["recorded"]


def test_a_take_needs_every_voices_consent():
    assert client.post("/api/recording/IS04?voices=AG", content=wav()).status_code == 400
    assert client.post("/api/recording/IS04?consent=1", content=wav()).status_code == 400
    assert not (recordings_dir() / "dev" / "IS04.wav").exists()


def test_a_take_is_saved_by_its_id_and_a_retake_keeps_the_old_one():
    r = client.post(f"/api/recording/IS04{CONSENT}", content=wav(3.0))
    assert r.status_code == 200 and r.json()["seconds"] == 3.0
    saved = recordings_dir() / "dev" / "IS04.wav"
    with wave.open(str(saved)) as w:
        assert (w.getnchannels(), w.getframerate()) == (1, 48000)
    assert client.get("/api/recording/IS04").content[:4] == b"RIFF"
    with open(recordings_dir() / "voices.csv", newline="") as f:
        assert [(row["call_id"], row["voices"], row["publish_ok"]) for row in csv.DictReader(f)] == [("IS04", "AG,PG", "0")]

    assert client.post("/api/label/IS04", json={"t0": 1.2, "labeller": "AG"}).status_code == 200
    assert client.post(f"/api/recording/IS04{CONSENT}", content=wav(4.0)).status_code == 409
    assert client.post(f"/api/recording/IS04{CONSENT}&replace=1", content=wav(4.0)).status_code == 200
    assert len(list((recordings_dir() / "replaced").glob("IS04-*.wav"))) == 1
    assert "IS04" not in read_labels(labels_path())  # the old take's times don't fit the new one
    # transcribe-set reads only the split's own folder, so a replaced take is never transcribed
    assert [p.name for p in (recordings_dir() / "dev").iterdir()] == ["IS04.wav"]
    assert not list((recordings_dir() / "incoming").iterdir())


def test_unreadable_or_silent_takes_are_refused():
    assert client.post(f"/api/recording/IS05{CONSENT}", content=b"not audio").status_code == 400
    assert client.post(f"/api/recording/IS05{CONSENT}", content=wav(0.3)).status_code == 400
    assert not (recordings_dir() / "dev").exists() or not list((recordings_dir() / "dev").iterdir())
    assert not list((recordings_dir() / "incoming").iterdir())
    assert client.post(f"/api/recording/NOPE{CONSENT}", content=wav()).status_code == 404


def test_labels_are_rounded_to_half_seconds_and_checked_like_the_sheet():
    assert client.post("/api/label/IS06", json={"t0": 1, "labeller": "AG"}).status_code == 409  # not recorded
    client.post(f"/api/recording/IS06{CONSENT}", content=wav(10.0))
    assert client.post("/api/label/IS06", json={"t0": 1.2}).status_code == 400  # no labeller
    assert client.post("/api/label/IS06", json={"t0": 6, "t_ask": 4, "labeller": "AG"}).status_code == 400
    assert client.post("/api/label/IS06", json={"t0": 30, "labeller": "AG"}).status_code == 400  # after the end
    row = client.post("/api/label/IS06", json={"t0": 1.2, "t_ask": 7.76, "labeller": "AG", "notes": "fan"}).json()
    assert (row["t0"], row["t_ask"], row["split"], row["pattern"], row["languages"]) == ("1", "8", "dev", "7", "mr")
    label = read_labels(labels_path())["IS06"]
    assert (label.t0, label.t_ask, label.is_scam, label.set) == (1.0, 8.0, True, "IN-scam")
    assert label.labelled_at.endswith("+05:30")


def test_a_genuine_call_gets_no_times():
    client.post(f"/api/recording/IG03{CONSENT}", content=wav())
    assert client.post("/api/label/IG03", json={"t0": 1, "labeller": "AG"}).status_code == 400
    row = client.post("/api/label/IG03", json={"labeller": "AG"}).json()
    assert (row["is_scam"], row["t0"], row["t_ask"]) == ("0", "", "")
