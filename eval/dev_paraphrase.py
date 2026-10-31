"""Dev only: the dev scam scripts rewritten without the baseline's keywords (eval/scripts/in-paraphrase-dev.json),
as text with estimated timings, through one run (A, B or C), with the next line. Before the freeze; never a test result.

    python eval/dev_paraphrase.py A runs/dev/dev-paraphrase-A.json     # B and C are PAID (Muse Spark)
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from teesrakaan.cli import _run  # noqa: E402
from teesrakaan.metrics import Outcome, results_table, summarize_by  # noqa: E402
from teesrakaan.scripts import load_scripts, to_call  # noqa: E402
from teesrakaan.simulate import Timing, simulate  # noqa: E402

run, out_path = sys.argv[1], Path(sys.argv[2])
judge, options, merge = _run(run)
outcomes = []
for s in load_scripts(REPO / "eval/scripts/in-paraphrase-dev.json"):
    call = to_call(s)
    r = simulate(call, judge, Timing(), **options)
    listener = r.listener
    outcomes.append(Outcome(
        call.id, s["set"], True, int(r.level), r.t_warn, r.t_red,
        predictions=tuple((p.step, p.made_at, p.said_at if p.came_true else None) for p in listener.predictions),
        found=tuple((f.id, f.said_at, f.found_at) for f in listener.found.values()),
    ))
out = {"split": "dev", "run": run, "calls_from": "eval/scripts/in-paraphrase-dev.json (text, estimated timings)",
       "by_set": summarize_by(outcomes, "set"), "calls": [o.__dict__ for o in outcomes]}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(results_table([out]))
for o in outcomes:
    print(o.call_id, "level", o.level, "t_warn", o.t_warn, "signals", [f[0] for f in o.found])
