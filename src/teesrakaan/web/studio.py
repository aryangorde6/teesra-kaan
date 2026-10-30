"""The recording studio: record the re-enactments and label them by listening, on the laptop that hears the call.

Local only. `teesrakaan studio` serves it on 127.0.0.1, it refuses any other client, and the
hosted page never mounts it. It shows each script card, records the room the way the live page
hears it, saves `data/recordings/<split>/<ID>.wav`, and writes `t0` and `t_ask` into
`data/labels-in.csv` (docs/labelling.md). It never transcribes or judges anything, so a label is
always made before the system's output on that call has been seen, and test recordings stay
unsent until the freeze.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse

from .. import config
from ..labels import COLUMNS, read_labels
from ..scripts import load_scripts, load_split

STATIC = Path(__file__).parent / "studio_static"
SCRIPTS = config.REPO_ROOT / "eval" / "scripts"
MAX_RECORDING_BYTES = 60 * 1024 * 1024
MAX_SECONDS = 10 * 60  # the batch endpoint's limit, and far longer than any card
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
LOOPBACK = {"127.0.0.1", "::1"}
VOICES = ("call_id", "voices", "consent", "publish_ok", "recorded_at", "seconds")

app = FastAPI(title="Teesra Kaan studio", docs_url=None, redoc_url=None)


@app.middleware("http")
async def local_only(request: Request, call_next):
    if request.client is None or request.client.host not in LOOPBACK:
        return PlainTextResponse("The studio runs only on this laptop.", status_code=403)
    return await call_next(request)


def recordings_dir() -> Path:
    return config.data_dir() / "recordings"


def labels_path() -> Path:
    return config.data_dir() / "labels-in.csv"


def cards() -> dict[str, dict]:
    split = load_split(SCRIPTS / "split.csv")
    out = {}
    for name in ("in-scam.json", "in-genuine.json"):
        for s in load_scripts(SCRIPTS / name):
            out[s["id"]] = {**s, "split": split[s["id"]]}
    return out


def _card(card_id: str) -> dict:
    card = cards().get(card_id)
    if card is None:
        raise HTTPException(404, f"No script {card_id}.")
    return card


def recording(card: dict) -> Path:
    return recordings_dir() / card["split"] / f"{card['id']}.wav"


def _labels() -> dict[str, dict[str, str]]:
    path = labels_path()
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {row["call_id"]: row for row in csv.DictReader(f)}


def _now() -> str:
    return dt.datetime.now(IST).isoformat(timespec="minutes")


def _seconds(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True)
    return round(float(out.stdout.strip()), 1)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "studio.html")


@app.get("/static/{name}")
def static(name: str) -> FileResponse:
    path = STATIC / name
    if path.parent != STATIC or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/api/cards")
def list_cards() -> list[dict]:
    """Dev cards first, as they're recorded first; each with whether it's recorded and labelled yet."""
    labels = _labels()
    out = []
    for card in sorted(cards().values(), key=lambda c: (c["split"] != "dev", c["id"])):
        out.append({
            "id": card["id"], "set": card["set"], "split": card["split"], "language": card["language"],
            "pattern": card.get("pattern", 0), "kind": card.get("kind", ""), "roles": card.get("roles"),
            "lines": card["lines"], "is_scam": card["set"] == "IN-scam",
            "recorded": recording(card).exists(), "label": labels.get(card["id"]),
        })
    return out


@app.post("/api/recording/{card_id}")
async def save_recording(card_id: str, request: Request) -> dict:
    """The browser's recording (any format ffmpeg reads) → `<split>/<ID>.wav`, 48 kHz mono. Needs every voice's
    written consent. An earlier take is moved to `recordings/replaced/`, never deleted, and its label is cleared,
    because its times belong to the old take."""
    card = _card(card_id)
    q = request.query_params
    voices = q.get("voices", "").strip()
    if q.get("consent") != "1" or not voices:
        raise HTTPException(400, "Every voice on the call must have given written consent (docs/recording.md).")
    body = await request.body()
    if not body or len(body) > MAX_RECORDING_BYTES:
        raise HTTPException(413, "Send one recording, up to 60 MB.")
    path = recording(card)
    if path.exists() and q.get("replace") != "1":
        raise HTTPException(409, f"{card_id} is already recorded. Record it again only to replace that take.")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Converted outside the split's folder, which transcribe-set reads whole, so a half-written take is never sent.
    tmp = recordings_dir() / "incoming" / f"{card_id}.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", "pipe:0", "-ac", "1", "-ar", "48000",
                        "-c:a", "pcm_s16le", "-map_metadata", "-1", str(tmp)],
                       input=body, check=True, capture_output=True)
        seconds = _seconds(tmp)
    except (subprocess.CalledProcessError, ValueError) as exc:
        tmp.unlink(missing_ok=True)
        raise HTTPException(400, "That recording couldn't be read. Try again.") from exc
    if not 1 <= seconds <= MAX_SECONDS:
        tmp.unlink(missing_ok=True)
        raise HTTPException(400, "A recording must be between 1 second and 10 minutes long.")
    if path.exists():
        _drop_label(card_id)  # first: if the sheet can't be rewritten, nothing has moved
        old = recordings_dir() / "replaced" / f"{card_id}-{dt.datetime.now(IST):%Y%m%d-%H%M%S}.wav"
        old.parent.mkdir(parents=True, exist_ok=True)
        path.rename(old)
    tmp.rename(path)
    _log_voices(card_id, voices, q.get("publish") == "1", seconds)
    return {"id": card_id, "path": str(path.relative_to(config.data_dir().parent)), "seconds": seconds}


@app.get("/api/recording/{card_id}")
def get_recording(card_id: str) -> FileResponse:
    path = recording(_card(card_id))
    if not path.exists():
        raise HTTPException(404, f"{card_id} isn't recorded yet.")
    return FileResponse(path, media_type="audio/wav")


def _log_voices(card_id: str, voices: str, publish_ok: bool, seconds: float) -> None:
    """Who spoke on each take, and whether they agreed to publication: kept next to the audio, never committed."""
    path = recordings_dir() / "voices.csv"
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VOICES)
        if new:
            writer.writeheader()
        writer.writerow({"call_id": card_id, "voices": voices, "consent": "written",
                         "publish_ok": int(publish_ok), "recorded_at": _now(), "seconds": seconds})


def _write_labels(rows: dict[str, dict[str, str]]) -> None:
    """Checked with the same rules as `teesrakaan labels` before anything is written."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows.values():
        writer.writerow({c: row.get(c, "") for c in COLUMNS})
    path = labels_path()
    tmp = path.with_suffix(".part.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(buf.getvalue(), encoding="utf-8")
    try:
        read_labels(tmp)
    except ValueError as exc:
        tmp.unlink()
        raise HTTPException(400, str(exc).split("\n", 1)[-1]) from exc
    tmp.replace(path)


def _drop_label(card_id: str) -> None:
    rows = _labels()
    if rows.pop(card_id, None) is not None:
        _write_labels(rows)


def _half(value) -> str:
    """Seconds, rounded to the nearest half second as docs/labelling.md asks; '' for none."""
    if value in (None, ""):
        return ""
    seconds = float(value)
    if seconds < 0:
        raise HTTPException(400, "Times can't be negative.")
    return f"{round(seconds * 2) / 2:g}"


@app.post("/api/label/{card_id}")
async def save_label(card_id: str, request: Request) -> dict:
    """`t0` and `t_ask` marked by listening to this take. The set, split, pattern and languages come from the
    script, never typed, so they can't drift from split.csv."""
    card = _card(card_id)
    path = recording(card)
    if not path.exists():
        raise HTTPException(409, f"Record {card_id} before labelling it.")
    body = await request.json()
    labeller = str(body.get("labeller", "")).strip()
    if not labeller:
        raise HTTPException(400, "Add your initials as the labeller.")
    t0, t_ask = _half(body.get("t0")), _half(body.get("t_ask"))
    length = _seconds(path)
    if any(t and float(t) > length + 0.5 for t in (t0, t_ask)):
        raise HTTPException(400, "A time is after the end of the recording.")
    rows = _labels()
    rows[card_id] = {
        "call_id": card_id, "set": card["set"], "split": card["split"],
        "is_scam": "1" if card["set"] == "IN-scam" else "0", "pattern": str(card.get("pattern", 0)),
        "languages": card["language"], "t0": t0, "t_ask": t_ask, "ftc_class": "",
        "labeller": labeller, "labelled_at": _now(), "notes": str(body.get("notes", "")).strip(),
    }
    _write_labels(rows)
    return rows[card_id]
