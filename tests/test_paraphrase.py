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
