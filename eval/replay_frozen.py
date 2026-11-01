"""The frozen test run, replayed offline from what it saved: no key, no network, no cost.

The run (eval/after_freeze.sh, Nov 1, 2026, 12:02-12:29 IST, on the eval-freeze tag) transcribed each test call
once and asked Muse Spark each question once. evidence/ keeps both: every transcription session, with its events
and the time each arrived, and every Muse Spark reply the run used. Replayed through the same code, they give the
same outcome for every call, and the README's tables.

    python eval/replay_frozen.py           # replays every run, checks it against evidence/results/, prints the tables
    python eval/replay_frozen.py collect   # the development machine only: copies the run's sessions, replies and
                                           # results from data/ and runs/ into evidence/, after the same check

A reply that isn't saved stops the replay (LookupError): nothing here ever calls the API.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from teesrakaan import cli, spark  # noqa: E402
from teesrakaan.metrics import results_table  # noqa: E402

EVIDENCE = REPO / "evidence"
# (transcripts, labels, split, run, results file), as eval/after_freeze.sh ran them
RUNS = (
    [("ftc-test", "eval/ftc-test-labels.csv", "test", r, f"eval-test/ftc-{r}.json") for r in ("A", "B", "C", "C-no-speakers")]
    + [("synth-test", "eval/synth-labels.csv", "test", r, f"eval-synth/results-test-{r}.json") for r in ("A", "B", "C")]
    + [("synth-paraphrase", "eval/synth-labels.csv", "paraphrase", r, f"eval-synth/results-paraphrase-{r}.json")
       for r in ("A", "B", "C")]
)
# each table from its runs, in the order after_freeze.sh's glob gave them
TABLES = {"eval-test/table.md": "eval-test/ftc-", "eval-synth/table-test.md": "eval-synth/results-test-",
          "eval-synth/table-paraphrase.md": "eval-synth/results-paraphrase-"}


def replay(transcripts: Path, replies: Path, out: Path) -> set[Path]:
    """Every run, through the evaluation's own code, with Muse Spark's saved replies in place of the API."""
    used: set[Path] = set()

    class Saved(spark.ReplayClient):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(replies)

        def __call__(self, system: str, user: str, schema: dict | None = None):
            used.add(self._cache_path(self.request(system, user, schema)))
            return super().__call__(system, user, schema)

    spark.SparkClient = Saved  # the runs build their judge from teesrakaan.spark.SparkClient
    for calls, labels, split, run, name in RUNS:
        cli.cmd_eval(argparse.Namespace(calls=str(transcripts / calls), labels=str(REPO / labels), split=split,
                                        run=run, out=str(out / name)))
    return used


# The one call the saved replies can't replay exactly. spark.py saves no reply cut off at the output limit, and one
# of this call's replies in the C run was never saved; the same question (one voice, so the same with speakers
# merged) was answered in full and saved during the C-no-speakers run (12:21). Replayed with that reply, the call
# is still amber, 2.7 s earlier; no number in the tables changes. The run's token count includes the unsaved reply.
KNOWN = {"eval-test/ftc-C.json": {"ftc-0b89b1bb64"}}


def close(x, y) -> bool:
    """Equal, but for times up to 0.25 s apart: the keyword runs time their own judge by the clock, so a busy
    machine shifts them by milliseconds. The tables are compared exactly."""
    if isinstance(x, float) or isinstance(y, float):
        return isinstance(x, (int, float)) and isinstance(y, (int, float)) and abs(x - y) < 0.25
    if isinstance(x, dict):
        return isinstance(y, dict) and x.keys() == y.keys() and all(close(x[k], y[k]) for k in x)
    if isinstance(x, list):
        return isinstance(y, list) and len(x) == len(y) and all(close(a, b) for a, b in zip(x, y))
    return x == y


def same(name: str, a: Path, b: Path) -> bool:
    """The same outcomes, call by call; only the folder the calls were read from differs."""
    x, y = (json.loads(p.read_text(encoding="utf-8")) for p in (a, b))
    for r in (x, y):
        r.pop("calls_from")
        if name in KNOWN:
            r.pop("usage"), r.pop("usd_per_minute_list_price")
            r["calls"] = [c for c in r["calls"] if c["call_id"] not in KNOWN[name]]
    return close(x, y)


def check(out: Path, results: Path) -> None:
    differ = [name for *_, name in RUNS if not same(name, out / name, results / name)]
    if differ:
        raise SystemExit("Not the frozen run's outcomes: " + ", ".join(differ))
    known = sum(len(ids) for ids in KNOWN.values())
    print(f"\nAll {len(RUNS)} runs match the frozen run's results, call by call, but for {known} call explained "
          f"in eval/replay_frozen.py (KNOWN).\n")


def main() -> None:
    collect = sys.argv[1:] == ["collect"]
    out = REPO / "runs" / "replay-frozen"
    if collect:
        used = replay(REPO / "data" / "transcripts", REPO / "data" / "cache" / "spark", out)
        check(out, REPO / "runs")
        shutil.rmtree(EVIDENCE, ignore_errors=True)
        for calls in sorted({r[0] for r in RUNS}):
            shutil.copytree(REPO / "data" / "transcripts" / calls, EVIDENCE / "transcripts" / calls)
        for path in used:
            dest = EVIDENCE / "spark-replies" / path.relative_to(REPO / "data" / "cache" / "spark")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        for *_, name in RUNS:
            (EVIDENCE / "results" / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / "runs" / name, EVIDENCE / "results" / name)
        for name in [*TABLES, "eval-synth/keywords-paraphrase.txt"]:
            shutil.copy2(REPO / "runs" / name, EVIDENCE / "results" / name)
        shutil.copy2(REPO / "runs" / "after-freeze-1202.log", EVIDENCE / "results" / "after-freeze-1202.log")
        print(f"evidence/: {len(used)} Muse Spark replies, the sessions of {len({r[0] for r in RUNS})} sets, "
              f"{len(RUNS)} results")
        return
    replay(EVIDENCE / "transcripts", EVIDENCE / "spark-replies", out)
    check(out, EVIDENCE / "results")
    for table, prefix in TABLES.items():
        names = [name for *_, name in RUNS if name.startswith(prefix)]
        text = results_table([json.loads((out / name).read_text(encoding="utf-8")) for name in names])
        if text.strip() != (EVIDENCE / "results" / table).read_text(encoding="utf-8").strip():
            raise SystemExit(f"{table} differs from the frozen run's")
        print(text)
    print("The tables above are the frozen run's (evidence/results/), unchanged.")


if __name__ == "__main__":
    main()
