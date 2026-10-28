"""The FTC robocall sample: NCSU's Robocall Audio Dataset, pinned to one commit.

The recordings come from the FTC's Project Point of No Entry. The data is in the
public domain; the dataset's README text is CC BY-ND, so it's downloaded for
reference but not copied into this repo. Only the 200 sampled English calls are
fetched, and every file is checked against its git blob hash.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

from .labels import sample_ftc

REPO = "wspr-ncsu/robocall-audio-dataset"
COMMIT = "5aa6f3bfa8563ce8c1c75ebf8a2271e6ff6b4272"  # main, 2024-07-25
RAW = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/"
TREE = f"https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1"
DOCS = ("metadata.csv", "README.md", "LICENSE.md")
_SAFE_NAME = re.compile(r"^[\w.-]+\.wav$")


def english_file_names(metadata: Path) -> list[str]:
    """Distinct English recordings. Some recordings are listed under two FTC cases; each counts once."""
    with open(metadata, newline="", encoding="utf-8") as f:
        names = {row["file_name"] for row in csv.DictReader(f) if row["language"] == "en"}
    return sorted(names)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def local_name(file_name: str) -> str:
    name = file_name.rsplit("/", 1)[-1]
    if not _SAFE_NAME.match(name):
        raise ValueError(f"unexpected file name in metadata: {file_name!r}")
    return name


def _get(url: str, tries: int = 4, timeout: float = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "teesra-kaan-eval"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError("unreachable")


def fetch(dest: Path, log: Callable[[str], None] = print) -> Path:
    """Downloads the metadata and the sampled audio into `dest`; resumable. Returns the sample sheet."""
    dest.mkdir(parents=True, exist_ok=True)
    for name in DOCS:
        if not (dest / name).exists():
            (dest / name).write_bytes(_get(RAW + name))
    tree = {item["path"]: item for item in json.loads(_get(TREE))["tree"] if item["type"] == "blob"}
    sample = sample_ftc(english_file_names(dest / "metadata.csv"))

    audio = dest / "audio"
    audio.mkdir(exist_ok=True)
    rows = []
    for i, (file_name, split) in enumerate(sorted(sample.items(), key=lambda kv: (kv[1], kv[0])), 1):
        expected = tree[file_name]["sha"]
        path = audio / local_name(file_name)
        if not (path.exists() and git_blob_sha(path.read_bytes()) == expected):
            data = _get(RAW + file_name)
            if git_blob_sha(data) != expected:
                raise ValueError(f"{file_name}: hash doesn't match the pinned commit")
            path.write_bytes(data)
            log(f"[{i}/{len(sample)}] {file_name} ({len(data) // 1024} KB)")
        rows.append({"file_name": file_name, "split": split, "path": str(path.relative_to(dest)),
                     "bytes": path.stat().st_size, "git_blob_sha": expected})

    sheet = dest / "sample.csv"
    with open(sheet, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (dest / "SOURCE.txt").write_text(
        f"NCSU Robocall Audio Dataset, https://github.com/{REPO}, commit {COMMIT}.\n"
        "Recordings from the FTC's Project Point of No Entry. The data is in the public domain;\n"
        "the dataset's README text is CC BY-ND. Sample: English recordings sorted by\n"
        "sha256(file_name), first 200, first 50 of those dev (docs/evaluation-rule.md).\n",
        encoding="utf-8",
    )
    return sheet


def call_id(file_name: str) -> str:
    return "ftc-" + hashlib.sha256(file_name.encode("utf-8")).hexdigest()[:10]


def to_calls(dest: Path, split: str) -> list[Path]:
    """Call files for one split, from the dataset's own transcripts, spread evenly over each recording.

    These are for offline runs only. The real evaluation transcribes the audio with Muse Voice Transcribe.
    """
    import wave

    with open(dest / "sample.csv", newline="", encoding="utf-8") as f:
        sample = {row["file_name"]: row for row in csv.DictReader(f) if row["split"] == split}
    transcripts: dict[str, str] = {}
    with open(dest / "metadata.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["file_name"] in sample:
                transcripts.setdefault(row["file_name"], " ".join(row["transcript"].split()))
    out = dest / "calls"
    out.mkdir(exist_ok=True)
    paths = []
    for file_name, row in sorted(sample.items()):
        with wave.open(str(dest / row["path"])) as w:
            seconds = w.getnframes() / w.getframerate()
        call = {
            "id": call_id(file_name),
            "set": "FTC",
            "language": "en",
            "file_name": file_name,
            "note": "Dataset transcript, words spread evenly over the recording. Offline runs only.",
            "turns": [{"speaker": "caller", "start": 0.0, "end": round(seconds, 2), "text": transcripts[file_name]}],
        }
        path = out / f"{call['id']}.json"
        path.write_text(json.dumps(call, ensure_ascii=False, indent=1), encoding="utf-8")
        paths.append(path)
    return paths
