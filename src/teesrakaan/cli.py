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
from .messages import LANGS, warning
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
    text = build_report(call, result.listener, args.lang).to_markdown()
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)


def cmd_eval(args: argparse.Namespace) -> None:
    labels = read_labels(args.labels)
    outcomes = []
    for path in sorted(Path(args.calls).glob("*.json")):
        call = load_call(path)
        label = labels.get(call.id)
        if label is None or label.split != args.split:
            continue
        if args.no_speakers:
            call = merge_speakers(call)
        result = simulate(call, _judge(args.judge), Timing())
        outcomes.append(Outcome(
            call.id, label.set, label.is_scam, int(result.level),
            result.t_warn, result.t_red, label.t0, label.t_ask, label.languages, label.ftc_class,
        ))
    # FTC sales and "other" robocalls are illegal calls, not genuine ones: reported by class, never as false alarms.
    scored = [o for o in outcomes if o.set != "FTC" or o.ftc_class == "impersonation"]
    report = {
        "split": args.split,
        "judge": args.judge,
        "rules": RULES_VERSION,
        "speaker_separation": not args.no_speakers,
        "by_set": summarize_by(scored, "set"),
        "by_language": summarize_by(scored, "language"),
        "ftc_by_class": ftc_summary(o for o in outcomes if o.set == "FTC"),
        "calls": [o.__dict__ for o in outcomes],
    }
    out = Path(args.out or f"runs/eval-{date.today().isoformat()}/results-{args.split}-{args.judge}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, s in report["by_set"].items():
        print(f"{name}: caught {s['caught_red_or_amber']['text']} (red {s['caught_red']['text']}), "
              f"red false alarms {s['false_alarms_red']['text']}")
    for name, row in report["ftc_by_class"].items():
        print(f"FTC {name}: warned {row['warned_text']} (red {row['red_text']})")
    print(f"wrote {out}")


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


def cmd_ping(args: argparse.Namespace) -> None:
    """One tiny Spark call, to check the key and that the credits pay for it."""
    from .spark import SparkClient

    done = SparkClient(max_output_tokens=16, reasoning_effort=None, cache_dir=Path(args.scratch))(
        "Reply with the single word: ok", f"ping {date.today().isoformat()}", None
    )
    print(f"reply {done.text!r}, {done.input_tokens} in / {done.output_tokens} out tokens, {done.latency:.2f} s")


def cmd_budget(args: argparse.Namespace) -> None:
    from .budget import Ledger, meta_cap

    s = Ledger("meta", meta_cap()).summary()
    print(f"meta: ${s.spent_usd:.4f} spent, ${s.reserved_usd:.4f} reserved, ${s.remaining_usd:.2f} left "
          f"of the ${s.cap_usd:.2f} stop, {s.calls} calls")


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
    p.add_argument("--out")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("eval", help="run every labelled call in a folder and write results.json")
    p.add_argument("calls")
    p.add_argument("--labels", required=True)
    p.add_argument("--split", choices=("dev", "test"), default="dev")
    p.add_argument("--judge", default="keywords")
    p.add_argument("--no-speakers", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_eval)

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

    p = sub.add_parser("budget", help="what the Meta API has cost so far, against the $120 stop")
    p.set_defaults(func=cmd_budget)

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
