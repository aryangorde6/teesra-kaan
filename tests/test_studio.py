import csv
import io
import json
import math
import struct
import wave

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from teesrakaan import voice  # noqa: E402
from teesrakaan.labels import read_labels  # noqa: E402
from teesrakaan.messages import voice_lines  # noqa: E402
from teesrakaan.web.studio import _seconds, app, labels_path, recordings_dir  # noqa: E402

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


def tone(seconds: float, quiet: float = 1.0, rate: int = 16000) -> bytes:
    """A 440 Hz tone with `quiet` seconds of silence before and after, like a line said into the mic."""
    pad = b"\x00\x00" * int(quiet * rate)
    sound = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(int(seconds * rate)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pad + sound + pad)
    return buf.getvalue()


def test_only_this_laptop_can_open_it():
    outside = TestClient(app, client=("192.168.1.20", 50000))
    assert outside.get("/").status_code == 403
    assert outside.get("/api/cards").status_code == 403
    assert client.get("/").status_code == 200
    assert client.get("/static/studio.js").status_code == 200


def test_cards_come_dev_first_from_the_fixed_split():
    cards = client.get("/api/cards").json()
    assert len(cards) == 89
    splits = [c["split"] for c in cards]
    assert splits == ["dev"] * 28 + ["test"] * 42 + ["paraphrase"] * 10 + ["voice"] * 9  # then the warning lines
    is04 = next(c for c in cards if c["id"] == "IS04")
    assert is04["is_scam"] and is04["pattern"] == 2 and is04["lines"] and not is04["recorded"]
    ip02 = next(c for c in cards if c["id"] == "IP02")
    assert ip02["is_scam"] and ip02["from"] == "IS02" and ip02["pattern"] == 3


def test_test_and_paraphrase_cards_come_in_the_fixed_recording_order():
    cards = client.get("/api/cards").json()
    for split, count in (("test", 42), ("paraphrase", 10)):
        assert [c["n"] for c in cards if c["split"] == split] == list(range(1, count + 1))
    assert [c["id"] for c in cards if c["split"] == "test"][:2] == ["IS30", "IG02"]
    assert all(c["n"] is None for c in cards if c["split"] == "dev")


def test_a_paraphrase_take_goes_to_its_own_folder_and_labels_as_a_scam():
    assert client.post(f"/api/recording/IP02{CONSENT}", content=wav(3.0)).status_code == 200
    assert (recordings_dir() / "paraphrase" / "IP02.wav").exists()
    r = client.post("/api/label/IP02", json={"t0": 0.5, "t_ask": 2, "labeller": "AG"})
    assert r.status_code == 200
    row = read_labels(labels_path())["IP02"]
    assert (row.set, row.split, row.is_scam, row.pattern) == ("IN-scam", "paraphrase", True, 3)


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


LINE = "?voices=AG&consent=1&publish=1"


def test_a_warning_line_needs_consent_and_the_ok_to_publish():
    assert client.post("/api/voice/W-red-IN-hi?voices=AG&consent=1", content=tone(2)).status_code == 400
    assert client.post("/api/voice/W-red-IN-hi?voices=AG&publish=1", content=tone(2)).status_code == 400
    assert client.post(f"/api/voice/W-nope{LINE}", content=tone(2)).status_code == 404
    assert not voice.audio_path("W-red-IN-hi").exists()


def test_a_warning_line_is_trimmed_saved_for_the_page_and_a_retake_keeps_the_old_one():
    r = client.post(f"/api/voice/W-red-IN-hi{LINE}", content=tone(2.0, quiet=1.5))
    assert r.status_code == 200
    assert 2.0 <= r.json()["seconds"] <= 2.7  # 1.5 s of quiet each side trimmed to under half a second in all
    assert _seconds(recordings_dir() / "voice" / "W-red-IN-hi.wav") == 5.0  # the untouched take, kept privately
    saved = json.loads(voice.meta_path("W-red-IN-hi").read_text(encoding="utf-8"))
    assert saved["lines"] == voice_lines()["W-red-IN-hi"]["lines"]
    assert list(voice.playable()) == ["W-red-IN-hi"]
    assert client.get("/api/voice/W-red-IN-hi").status_code == 200
    card = next(c for c in client.get("/api/cards").json() if c["id"] == "W-red-IN-hi")
    assert card["recorded"] and not card["stale"] and card["language"] == "hi"
    assert client.post(f"/api/voice/W-red-IN-hi{LINE}", content=tone(2)).status_code == 409
    assert client.post(f"/api/voice/W-red-IN-hi{LINE}&replace=1", content=tone(3)).status_code == 200
    assert len(list((recordings_dir() / "replaced").glob("W-red-IN-hi-*.m4a"))) == 1
    assert not list((recordings_dir() / "incoming").iterdir())
    with open(recordings_dir() / "voices.csv", newline="") as f:
        assert [(row["call_id"], row["publish_ok"]) for row in csv.DictReader(f)] == [("W-red-IN-hi", "1")] * 2


def test_a_silent_warning_line_is_refused():
    assert client.post(f"/api/voice/W-amber-mr{LINE}", content=wav(3.0)).status_code == 400  # nothing but a hum
    assert client.post(f"/api/voice/W-amber-mr{LINE}", content=b"not audio").status_code == 400
    assert not voice.audio_path("W-amber-mr").exists()
    assert not list((recordings_dir() / "incoming").iterdir())


def test_a_line_whose_words_changed_is_stale_until_recorded_again(monkeypatch):
    client.post(f"/api/voice/W-amber-en{LINE}", content=tone(2))
    old = voice_lines()
    changed = {**old, "W-amber-en": {**old["W-amber-en"], "lines": ["Careful", "New advice."]}}
    monkeypatch.setattr("teesrakaan.voice.voice_lines", lambda: changed)
    monkeypatch.setattr("teesrakaan.web.studio.voice_lines", lambda: changed)
    assert voice.playable() == {}
    card = next(c for c in client.get("/api/cards").json() if c["id"] == "W-amber-en")
    assert card["stale"] and not card["recorded"]


def _rms(path) -> float:
    with wave.open(str(path)) as w:
        frames = w.readframes(w.getnframes())
    samples = struct.unpack(f"<{len(frames) // 2}h", frames)
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def test_a_solo_take_is_saved_through_the_phone_band_keeps_the_raw_and_says_so():
    """Evaluation rule v1.5.1: one person reads the caller, the laptop says the listener's lines."""
    from teesrakaan import config
    from teesrakaan.web.studio import solo_raw

    assert next(c for c in client.get("/api/cards").json() if c["id"] == "IP02")["solo"] == []  # no listener audio yet
    (config.data_dir() / "solo" / "IP02").mkdir(parents=True)
    (config.data_dir() / "solo" / "IP02" / "2.wav").write_bytes(wav(1.0))
    cards = {c["id"]: c for c in client.get("/api/cards").json()}
    assert cards["IP02"]["solo"] == [2] and cards["IS04"]["solo"] == []
    assert client.get("/api/solo/IP02/2").content[:4] == b"RIFF"
    assert client.get("/api/solo/IP02/0").status_code == 404  # a caller line: the person says it
    assert client.post(f"/api/recording/IS04{CONSENT}&solo=1", content=wav()).status_code == 400  # not a paraphrase card

    rate = 16000  # a 6 kHz tone: above the phone band, so the saved take is far quieter than the raw one
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 6000 * i / rate))) for i in range(3 * rate)))
    assert client.post(f"/api/recording/IP02?voices=AG&consent=1&solo=1", content=buf.getvalue()).status_code == 200
    saved, raw = recordings_dir() / "paraphrase" / "IP02.wav", solo_raw("IP02")
    assert raw.exists() and _rms(saved) < _rms(raw) / 10
    with open(recordings_dir() / "voices.csv", newline="") as f:
        assert [row["voices"] for row in csv.DictReader(f)] == ["AG + listener: synthetic voice (Kokoro hf_alpha)"]
    assert client.post("/api/label/IP02", json={"t0": 0.5, "labeller": "AG", "notes": "fan on"}).status_code == 200
    assert read_labels(labels_path())["IP02"].notes == "solo take; fan on"

    # Recorded again by two people: the solo raw goes with the old take, and the label no longer says solo.
    assert client.post(f"/api/recording/IP02{CONSENT}&replace=1", content=wav(3.0)).status_code == 200
    assert not raw.exists() and len(list((recordings_dir() / "replaced").glob("IP02-*-solo-raw.wav"))) == 1
    assert client.post("/api/label/IP02", json={"t0": 0.5, "labeller": "AG"}).status_code == 200
    assert read_labels(labels_path())["IP02"].notes == ""
