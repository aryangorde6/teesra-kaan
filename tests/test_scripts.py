from pathlib import Path

from teesrakaan.scripts import load_scripts, load_split, to_call
from teesrakaan.transcript import CALLER

EVAL = Path(__file__).resolve().parent.parent / "eval" / "scripts"


def test_every_script_is_split_and_well_formed():
    split = load_split(EVAL / "split.csv")
    scripts = load_scripts(EVAL / "in-scam.json") + load_scripts(EVAL / "in-genuine.json")
    assert len(scripts) == 70 and {s["id"] for s in scripts} == split.keys()
    assert sum(v == "dev" for v in split.values()) == 28
    for s in scripts:
        assert s["language"] in {"hi", "mr", "en", "hi+en"}
        assert any(line[0] == CALLER for line in s["lines"])


def test_scripts_become_timed_calls():
    script = {"id": "X", "set": "IN-scam", "language": "hi", "pattern": 1,
              "lines": [["caller", "a b c d e f g h i j k l m"], ["listener", "haan"]]}
    call = to_call(script)
    assert call.turns[0].start == 0 and call.turns[0].end == 5.0
    assert call.turns[1].start == 5.6 and call.label["is_scam"]
