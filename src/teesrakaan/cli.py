"""teesrakaan: simulate a call, build its report, check labels, and run the offline evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .judge import SparkSized
from .keywords import KeywordJudge
from .labels import read_labels, split_scripts, write_template
from .messages import COUNTRIES, LANGS, warning
from .metrics import Outcome, ftc_summary, summarize_by
from .pricing import call_cost
from .report import build_report
from .signals import RULES_VERSION
from .simulate import Timing, replay, simulate
from .transcript import load_call, merge_speakers


def _judge(name: str):
    if name == "keywords":
        return SparkSized(KeywordJudge())
    raise SystemExit(f"unknown judge {name!r}: only 'keywords' runs offline (Muse Spark comes with the API key)")


# The runs in docs/evaluation-rule.md. The transcription ablations (no language hint,
# no keyword biasing) are run C on transcripts made with those settings.
RUNS = ("A", "B", "C", "C-no-speakers", "C-v1.2")


def _run(name: str):
    """(judge, Listener options, merge speakers?) for one run."""
    if name == "A":
        return SparkSized(KeywordJudge()), {}, False
    from .judge import FreeFormJudge, SparkJudge
    from .signals import SCAM, decide_freeform
    from .spark import SparkClient

    if name == "B":
        return FreeFormJudge(SparkClient()), {"signals": (SCAM,), "decide": decide_freeform, "verify_quotes": False}, False
    if name in ("C", "C-no-speakers"):
        from .judge import CheckedJudge

        client = SparkClient()
        return CheckedJudge(SparkJudge(client), FreeFormJudge(client)), {}, name == "C-no-speakers"
    if name == "C-v1.2":  # dev only: Spark's signals with the two-signal rules, as before Oct 30
        return SparkJudge(SparkClient()), {}, False
    raise SystemExit(f"unknown run {name!r}; one of {RUNS}")


def _load(path: Path):
    """A call file, or a saved transcription session (its id is the file name)."""
    from .asr import session_to_call

    data = json.loads(path.read_text(encoding="utf-8"))
    return session_to_call(data, path.stem) if "events" in data else load_call(path)


def cmd_simulate(args: argparse.Namespace) -> None:
    call = load_call(args.call)
    if args.no_speakers:
        call = merge_speakers(call)
    result = simulate(call, _judge(args.judge), Timing())
    replay(result, speed=args.speed if args.realtime else None)
    listener = result.listener
    quotes = {sid: f.quote for sid, f in listener.found.items()}
    print()
    print(json.dumps(warning(listener.alarm, quotes, args.lang), ensure_ascii=False, indent=2))
    cost = call_cost(call.duration, listener.input_tokens, listener.output_tokens)
    print(f"\n{listener.judge_calls} judge calls, ~{listener.input_tokens} input tokens; "
          f"as Muse Spark + Voice Transcribe: ~${cost:.4f} for {call.duration:.0f} s of audio")


def cmd_report(args: argparse.Namespace) -> None:
    call = load_call(args.call)
    result = simulate(call, _judge(args.judge), Timing())
    text = build_report(call, result.listener, args.lang, country=args.country).to_markdown()
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)


def cmd_eval(args: argparse.Namespace) -> None:
    labels = read_labels(args.labels)
    judge, options, merge = _run(args.run)
    outcomes = []
    usage = {"audio_seconds": 0.0, "judge_calls": 0, "input_tokens": 0, "output_tokens": 0}
    for path in sorted(Path(args.calls).glob("*.json")):
        call = _load(path)
        label = labels.get(call.id)
        if label is None or label.split != args.split:
            continue
        if merge:
            call = merge_speakers(call)
        timing = Timing(judge_latency=None) if any(t.heard_times for t in call.turns) else Timing()
        result = simulate(call, judge, timing, **options)
        usage["audio_seconds"] += call.duration
        usage["judge_calls"] += result.listener.judge_calls
        usage["input_tokens"] += result.listener.input_tokens
        usage["output_tokens"] += result.listener.output_tokens
        listener = result.listener
        outcomes.append(Outcome(
            call.id, label.set, label.is_scam, int(result.level),
            result.t_warn, result.t_red, label.t0, label.t_ask, label.languages, label.ftc_class,
            predictions=tuple((p.step, p.made_at, p.said_at if p.came_true else None) for p in listener.predictions),
            found=tuple((f.id, f.said_at, f.found_at) for f in listener.found.values()),
        ))
    # FTC sales and "other" robocalls are illegal calls, not genuine ones: reported by class, never as false alarms.
    scored = [o for o in outcomes if o.set != "FTC" or o.ftc_class == "impersonation"]
    report = {
        "split": args.split,
        "run": args.run,
        "calls_from": args.calls,
        "rules": RULES_VERSION,
        # The naive guess learns from the calls it's scored on, so it runs on dev only.
        "by_set": summarize_by(scored, "set", naive=args.split == "dev"),
        "by_language": summarize_by(scored, "language", naive=args.split == "dev"),
        "ftc_by_class": ftc_summary(o for o in outcomes if o.set == "FTC"),
        "usage": usage,
        "usd_per_minute_list_price": round(
            call_cost(usage["audio_seconds"], usage["input_tokens"], usage["output_tokens"])
            / max(usage["audio_seconds"] / 60, 1e-9), 5),
        "calls": [o.__dict__ for o in outcomes],
    }
    out = Path(args.out or f"runs/eval-{date.today().isoformat()}/results-{args.split}-{args.run}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, s in report["by_set"].items():
        print(f"{name}: caught {s['caught_red_or_amber']['text']} (red {s['caught_red']['text']}), "
              f"red false alarms {s['false_alarms_red']['text']}")
        n = s["next_line"]
        if n["shown"]:
            print(f"{name}: next line came true {n['came_true']['text']}"
                  + (f" (naive guess {n['naive_guess']['text']})" if n["naive_guess"] else ""))
    for name, row in report["ftc_by_class"].items():
        print(f"FTC {name}: warned {row['warned_text']} (red {row['red_text']})")
    print(f"wrote {out}")


def cmd_table(args: argparse.Namespace) -> None:
    from .metrics import results_table

    print(results_table([json.loads(Path(p).read_text(encoding="utf-8")) for p in args.results]))


def cmd_keywords(args: argparse.Namespace) -> None:
    """For the paraphrase test: a rewritten script must match none of the baseline's keywords."""
    from .keywords import keyword_hits

    hits = keyword_hits(Path(args.text).read_text(encoding="utf-8"))
    for sid, words in hits:
        print(f"{sid}: {words!r}")
    print("no baseline keyword found" if not hits else f"{len(hits)} keyword matches: rewrite these")
    raise SystemExit(1 if hits else 0)


def cmd_split(args: argparse.Namespace) -> None:
    ids = [line.strip() for line in Path(args.ids).read_text(encoding="utf-8").splitlines() if line.strip()]
    for sid, split in sorted(split_scripts(ids).items()):
        print(f"{sid},{split}")


def cmd_ftc(args: argparse.Namespace) -> None:
    from .ftc import fetch

    sheet = fetch(Path(args.dest))
    print(f"wrote {sheet}")


def cmd_transcribe(args: argparse.Namespace) -> None:
    from .asr import transcribe_file

    settings = {"mode": args.mode}
    if args.no_language_hint:
        settings["languages"] = ()
    if args.no_keywords:
        settings["keywords"] = ()
    session = transcribe_file(args.audio, **settings)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(session.to_json(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(session.events)} events, {session.audio_seconds:.0f} s of audio -> {out}")


def cmd_transcribe_set(args: argparse.Namespace) -> None:
    import asyncio

    from .asr import transcribe_many

    settings = {}
    if args.no_language_hint:
        settings["languages"] = ()
    if args.no_keywords:
        settings["keywords"] = ()
    done = asyncio.run(transcribe_many(Path(args.audio_dir), Path(args.out), args.parallel, **settings))
    print(f"{done} recordings transcribed into {args.out}")


def cmd_ping(args: argparse.Namespace) -> None:
    """One tiny Spark call, to check the key and that the credits pay for it."""
    from .spark import SparkClient

    done = SparkClient(max_output_tokens=256, cache_dir=Path(args.scratch))(
        "Reply with the single word: ok", f"ping {date.today().isoformat()}", None
    )
    print(f"reply {done.text!r}, {done.input_tokens} in / {done.output_tokens} out tokens, {done.latency:.2f} s")


def cmd_demo_replies(args: argparse.Namespace) -> None:
    """Muse Spark's replies for every demo call, saved beside them, so the hosted page replays them free."""
    import shutil

    from .judge import CheckedJudge, FreeFormJudge, SparkJudge
    from .spark import SparkClient
    from .web.app import DEMO_REPLIES, _demo_calls, check_said, demo_events, example_texts

    used: set[Path] = set()

    class Saving(SparkClient):
        def __call__(self, system, user, schema=None):
            done = super().__call__(system, user, schema)
            used.add(self._cache_path(self.request(system, user, schema)))
            return done

    client = Saving()
    judge = CheckedJudge(SparkJudge(client), FreeFormJudge(client))
    for call in _demo_calls().values():
        events = demo_events(call, "en", judge=judge)
        levels = [e["warning"]["level"] for _, e in events if e["type"] == "alarm"]
        print(f"{call.id}: {' -> '.join(levels) or 'no warning'}")
    for lang, text in example_texts().items():
        print(f"example ({lang}): {check_said(text, lang, 'IN', judge)['warning']['level']}")
    if DEMO_REPLIES.exists():
        shutil.rmtree(DEMO_REPLIES)
    for path in sorted(used):
        dest = DEMO_REPLIES / path.relative_to(client.cache_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    print(f"{len(used)} replies saved in {DEMO_REPLIES}")


def cmd_budget(args: argparse.Namespace) -> None:
    import time

    from .budget import META_CREDIT_USD, Ledger, meta_cap, paid_until

    s = Ledger("meta", meta_cap()).summary()
    print(f"ledger:      ${s.spent_usd:.4f} spent, ${s.reserved_usd:.4f} reserved, {s.calls} calls")
    if s.reading is None:
        print("Meta's meter: never read (teesrakaan meter)")
    else:
        r = s.reading
        print(f"Meta's meter: ${r.credits_left_usd:.2f} of ${META_CREDIT_USD:.0f} credits left, balance Rs "
              f"{r.balance_inr:.2f}, read {(time.time() - r.ts) / 3600:.1f} h ago at ledger ${r.ledger_usd:.4f}")
    print(f"counted:     ${s.counted_usd:.4f}, ${s.remaining_usd:.2f} left of the ${s.cap_usd:.2f} stop; "
          f"paid calls end {paid_until():%Y-%m-%d %H:%M} UTC")
    print(f"paid calls:  {'REFUSED: ' + s.refusal if s.refusal else 'allowed'}")


def cmd_meter(args: argparse.Namespace) -> None:
    from .budget import Ledger, meta_cap

    Ledger("meta", meta_cap()).record_meter(args.credits_left, args.balance_inr, args.source, args.drift_ok)
    cmd_budget(args)


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("teesrakaan.web.app:app", host=args.host, port=args.port)


def cmd_labels(args: argparse.Namespace) -> None:
    if args.template:
        write_template(args.path)
        print(f"wrote an empty labelling sheet to {args.path}")
    else:
        print(f"{len(read_labels(args.path))} labels, no errors")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="teesrakaan", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("simulate", help="play a transcribed call to the listener and show the warnings")
    p.add_argument("call")
    p.add_argument("--judge", default="keywords")
    p.add_argument("--lang", choices=LANGS, default="en")
    p.add_argument("--realtime", action="store_true", help="print at the speed of the call")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--no-speakers", action="store_true", help="ablation: no speaker separation")
    p.set_defaults(func=cmd_simulate)

    p = sub.add_parser("report", help="the report pack for a call")
    p.add_argument("call")
    p.add_argument("--judge", default="keywords")
    p.add_argument("--lang", choices=LANGS, default="en")
    p.add_argument("--country", choices=COUNTRIES, default="IN", help="where to report: India (1930) or the US (FTC)")
    p.add_argument("--out")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("eval", help="run every labelled call in a folder and write results.json")
    p.add_argument("calls")
    p.add_argument("--labels", required=True)
    p.add_argument("--split", choices=("dev", "test"), default="dev")
    p.add_argument("--run", choices=RUNS, default="A", help="A keywords, B Spark free-form, C Teesra Kaan (B and C are PAID)")
    p.add_argument("--out")
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("keywords", help="list baseline keywords in a text file (the paraphrase test needs none)")
    p.add_argument("text")
    p.set_defaults(func=cmd_keywords)

    p = sub.add_parser("table", help="the results table from one or more results JSON files")
    p.add_argument("results", nargs="+")
    p.set_defaults(func=cmd_table)

    p = sub.add_parser("transcribe-set", help="PAID: transcribe every recording in a folder, several at a time")
    p.add_argument("audio_dir")
    p.add_argument("--out", required=True)
    p.add_argument("--parallel", type=int, default=8)
    p.add_argument("--no-language-hint", action="store_true", help="ablation")
    p.add_argument("--no-keywords", action="store_true", help="ablation")
    p.set_defaults(func=cmd_transcribe_set)

    p = sub.add_parser("split", help="assign script ids (one per line) to dev or test with the fixed seed")
    p.add_argument("ids")
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("ftc-fetch", help="download the 200 sampled FTC robocalls (public domain), pinned and hash-checked")
    p.add_argument("--dest", default="data/ftc")
    p.set_defaults(func=cmd_ftc)

    p = sub.add_parser("transcribe", help="PAID: stream one recording through Muse Voice Transcribe")
    p.add_argument("audio")
    p.add_argument("--out", required=True, help="where to save the session's events (JSON)")
    p.add_argument("--mode", default="DIARIZATION", choices=("DIARIZATION", "ENDPOINTING"))
    p.add_argument("--no-language-hint", action="store_true", help="ablation")
    p.add_argument("--no-keywords", action="store_true", help="ablation")
    p.set_defaults(func=cmd_transcribe)

    p = sub.add_parser("ping", help="PAID: one tiny Muse Spark call to check the key and credits")
    p.add_argument("--scratch", default="runs/ping-cache", help="cache folder, so a ping is never served from cache")
    p.set_defaults(func=cmd_ping)

    p = sub.add_parser("demo-replies", help="PAID once: save Muse Spark's replies for the demo calls, for the hosted page")
    p.set_defaults(func=cmd_demo_replies)

    p = sub.add_parser("budget", help="what the Meta API has cost so far, against the $100 stop")
    p.set_defaults(func=cmd_budget)

    p = sub.add_parser("meter", help="record Meta's own meter, as dev.meta.ai -> Billing shows it now")
    p.add_argument("--credits-left", type=float, required=True, help='"Free credits in use", in USD')
    p.add_argument("--balance-inr", type=float, required=True, help='"Current balance", in rupees')
    p.add_argument("--source", default="", help="where the reading came from, e.g. a screenshot's time")
    p.add_argument("--drift-ok", action="store_true", help="Meta's meter is ahead of the ledger and the cause is known")
    p.set_defaults(func=cmd_meter)

    p = sub.add_parser("serve", help="run the listener page")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("labels", help="check a labelling sheet, or write an empty one")
    p.add_argument("path")
    p.add_argument("--template", action="store_true")
    p.set_defaults(func=cmd_labels)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
