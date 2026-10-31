"""The synthetic set (docs/evaluation-rule.md, v1.5): which calls, and labels made from the scripts."""

import csv
import json
from pathlib import Path

from teesrakaan.labels import read_labels

EVAL = Path(__file__).resolve().parents[1] / "eval"


def _scripts(name):
    return json.loads((EVAL / "scripts" / name).read_text(encoding="utf-8"))["scripts"]


def test_every_hindi_marathi_and_english_test_script_and_paraphrase_is_in_it_and_nothing_else():
    with open(EVAL / "scripts/split.csv", newline="", encoding="utf-8") as f:
        split = {r["id"]: r["split"] for r in csv.DictReader(f)}
    spoken = ("hi", "mr", "en")
    want = {s["id"] for name in ("in-scam.json", "in-genuine.json") for s in _scripts(name)
            if split[s["id"]] == "test" and s["language"] in spoken}
    want |= {s["id"] for s in _scripts("in-paraphrase.json") if s["language"] in spoken}
    labels = read_labels(EVAL / "synth-labels.csv")
    assert set(labels) == want and len(want) == 42


def test_labels_are_synthetic_sets_with_times_from_the_audio_manifest():
    labels = read_labels(EVAL / "synth-labels.csv")
    manifest = json.loads((EVAL / "synth-manifest.json").read_text(encoding="utf-8"))
    asks = {s["id"]: s["ask"] for name in ("in-scam.json", "in-paraphrase.json") for s in _scripts(name)}
    for cid, label in labels.items():
        assert label.set == ("IN-synth-scam" if label.is_scam else "IN-synth-genuine")
        assert label.split == manifest[cid]["split"]
        starts = {line["start"] for line in manifest[cid]["lines"] if line["speaker"] == "caller"}
        if label.is_scam:
            assert label.t0 in starts and (label.t_ask is None or label.t_ask in starts)
            assert (label.t_ask is not None) == asks[cid]


def test_every_audio_file_has_a_hash():
    names = {line.split()[1] for line in (EVAL / "synth-audio.sha256").read_text().splitlines()}
    manifest = json.loads((EVAL / "synth-manifest.json").read_text(encoding="utf-8"))
    assert names == {"manifest.json"} | {f"{m['split']}/{cid}.wav" for cid, m in manifest.items()}
