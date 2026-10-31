"""The paraphrase test's scripts (docs/evaluation-rule.md, Robustness): which 10, and that no keyword is left."""

import csv
import json
import random
from pathlib import Path

from teesrakaan.keywords import keyword_hits
from teesrakaan.labels import SPLIT_SEED

SCRIPTS = Path(__file__).resolve().parents[1] / "eval/scripts"


def _load(name):
    return {s["id"]: s for s in json.loads((SCRIPTS / name).read_text(encoding="utf-8"))["scripts"]}


def _test_scam_ids():
    with open(SCRIPTS / "split.csv", newline="", encoding="utf-8") as f:
        return sorted(r["id"] for r in csv.DictReader(f) if r["set"] == "IN-scam" and r["split"] == "test")


def test_the_ten_are_drawn_from_the_test_scams_with_the_split_seed():
    picked = sorted(random.Random(SPLIT_SEED).sample(_test_scam_ids(), 10))
    assert sorted(s["from"] for s in _load("in-paraphrase.json").values()) == picked


def test_no_baseline_keyword_anywhere_in_them():
    for s in _load("in-paraphrase.json").values():
        text = "\n".join(line[1] for line in s["lines"])
        assert keyword_hits(text) == [], s["id"]


def test_each_keeps_its_scripts_pattern_language_ask_and_order_of_voices():
    scams = _load("in-scam.json")
    for pid, s in _load("in-paraphrase.json").items():
        source = scams[s["from"]]
        assert pid == "IP" + s["from"][2:]
        assert (s["pattern"], s["language"], s["ask"]) == (source["pattern"], source["language"], source["ask"])
        assert [line[0] for line in s["lines"]] == [line[0] for line in source["lines"]]


def test_the_set_is_scam_so_labels_and_runs_score_them_as_scams():
    assert json.loads((SCRIPTS / "in-paraphrase.json").read_text(encoding="utf-8"))["set"] == "IN-scam"


def test_keywords_counts_what_came_back_in_a_transcript(tmp_path, capsys):
    from teesrakaan.cli import main

    turns = [
        {"speaker": "A", "start": 0, "end": 4, "text": "Namaste, main ek sarkari daftar se baat kar raha hoon, OTP bata do."},
        {"speaker": "B", "start": 4, "end": 5, "text": "Police ko bataun?"},
        {"speaker": "A", "start": 5, "end": 9, "text": "Nahi, yeh baat apne tak rakhiye aur woh chhe ank padh dijiye."},
    ]
    (tmp_path / "IP99.json").write_text(json.dumps({"id": "IP99", "turns": turns}), encoding="utf-8")
    main(["keywords", str(tmp_path)])
    out = capsys.readouterr().out
    assert out.startswith("IP99: 1 in the caller's words, 2 in all: A5 ")


def test_the_dev_rewrites_cover_every_dev_scam_and_leave_no_keyword():
    with open(SCRIPTS / "split.csv", newline="", encoding="utf-8") as f:
        dev = sorted(r["id"] for r in csv.DictReader(f) if r["set"] == "IN-scam" and r["split"] == "dev")
    rewrites, scams = _load("in-paraphrase-dev.json"), _load("in-scam.json")
    assert sorted(s["from"] for s in rewrites.values()) == dev
    for pid, s in rewrites.items():
        source = scams[s["from"]]
        assert pid == "DP" + s["from"][2:]
        assert (s["pattern"], s["language"], s["ask"]) == (source["pattern"], source["language"], source["ask"])
        assert [line[0] for line in s["lines"]] == [line[0] for line in source["lines"]]
        assert keyword_hits("\n".join(line[1] for line in s["lines"])) == [], pid
