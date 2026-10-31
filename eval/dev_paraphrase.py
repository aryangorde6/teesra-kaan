"""Dev only: the dev scam scripts rewritten without the baseline's keywords (eval/scripts/in-paraphrase-dev.json),
through one run (A, B or C), with the next line: as text with estimated timings, or from a folder of their transcripts
(the synthetic speech of eval/synthetic_dev_paraphrase.py). Before the freeze; never a test result.

    python eval/dev_paraphrase.py A runs/dev/dev-paraphrase-A.json     # B and C are PAID (Muse Spark)
    python eval/dev_paraphrase.py C runs/dev/dev-paraphrase-synth-C.json data/transcripts/synth-dev-paraphrase
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from teesrakaan.cli import _load, _run  # noqa: E402
from teesrakaan.metrics import Outcome, results_table, summarize_by  # noqa: E402
from teesrakaan.scripts import load_scripts, to_call  # noqa: E402
from teesrakaan.simulate import Timing, simulate  # noqa: E402

run, out_path = sys.argv[1], Path(sys.argv[2])
transcripts = Path(sys.argv[3]) if len(sys.argv) > 3 else None
judge, options, merge = _run(run)
outcomes = []
for s in load_scripts(REPO / "eval/scripts/in-paraphrase-dev.json"):
    if transcripts is None:
        call, timing = to_call(s), Timing()
    elif (transcripts / f"{s['id']}.json").exists():
        call, timing = _load(transcripts / f"{s['id']}.json"), Timing(judge_latency=None)
    else:
        continue
    r = simulate(call, judge, timing, **options)
    listener = r.listener
    outcomes.append(Outcome(
        call.id, s["set"], True, int(r.level), r.t_warn, r.t_red,
        predictions=tuple((p.step, p.made_at, p.said_at if p.came_true else None) for p in listener.predictions),
        found=tuple((f.id, f.said_at, f.found_at) for f in listener.found.values()),
    ))
source = f"{transcripts} (SYNTHETIC: Kokoro voices, phone band)" if transcripts else "eval/scripts/in-paraphrase-dev.json (text, estimated timings)"
out = {"split": "dev", "run": run, "calls_from": source,
       "by_set": summarize_by(outcomes, "set"), "calls": [o.__dict__ for o in outcomes]}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(results_table([out]))
for o in outcomes:
    print(o.call_id, "level", o.level, "t_warn", o.t_warn, "signals", [f[0] for f in o.found])
