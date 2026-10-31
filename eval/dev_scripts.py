"""Dev only: the dev re-enactment scripts (eval/scripts/in-scam.json and in-genuine.json, split "dev" in split.csv) as
text with estimated timings, through one run. Test scripts are skipped unread. Before the freeze; never a test result.

    python eval/dev_scripts.py C runs/dev/in-dev-scripts-C-v1.4.json     # B and C are PAID (Muse Spark)
"""
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from teesrakaan.cli import _run  # noqa: E402
from teesrakaan.metrics import Outcome, results_table, summarize_by  # noqa: E402
from teesrakaan.playbook import PLAYBOOK_VERSION  # noqa: E402
from teesrakaan.scripts import load_scripts, to_call  # noqa: E402
from teesrakaan.signals import RULES_VERSION  # noqa: E402
from teesrakaan.simulate import Timing, simulate  # noqa: E402

run, out_path = sys.argv[1], Path(sys.argv[2])
with open(REPO / "eval/scripts/split.csv", newline="", encoding="utf-8") as f:
    dev = {r["id"] for r in csv.DictReader(f) if r["split"] == "dev"}
judge, options, merge = _run(run)
outcomes = []
for name in ("in-scam.json", "in-genuine.json"):
    for s in load_scripts(REPO / "eval/scripts" / name):
        if s["id"] not in dev:
            continue
        call = to_call(s)
        r = simulate(call, judge, Timing(), **options)
        listener = r.listener
        outcomes.append(Outcome(
            call.id, call.set, call.label["is_scam"], int(r.level), r.t_warn, r.t_red,
            predictions=tuple((p.step, p.made_at, p.said_at if p.came_true else None) for p in listener.predictions),
            found=tuple((f.id, f.said_at, f.found_at) for f in listener.found.values()),
        ))
out = {"split": "dev", "run": run, "calls_from": "eval/scripts (text, estimated timings)", "rules": RULES_VERSION,
       "playbook": PLAYBOOK_VERSION, "by_set": summarize_by(outcomes, "set", naive=True),
       "calls": [o.__dict__ for o in outcomes]}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(results_table([out]))
for o in outcomes:
    print(o.call_id, "scam" if o.is_scam else "genuine", "level", o.level, "signals", sorted(f[0] for f in o.found))
