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
from .metrics import Outcome, summarize_by
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
            result.t_warn, result.t_red, label.t0, label.t_ask, label.languages,
        ))
    report = {
        "split": args.split,
        "judge": args.judge,
        "rules": RULES_VERSION,
        "speaker_separation": not args.no_speakers,
        "by_set": summarize_by(outcomes, "set"),
        "by_language": summarize_by(outcomes, "language"),
        "calls": [o.__dict__ for o in outcomes],
    }
    out = Path(args.out or f"runs/eval-{date.today().isoformat()}/results-{args.split}-{args.judge}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, s in report["by_set"].items():
        print(f"{name}: caught {s['caught_red_or_amber']['text']} (red {s['caught_red']['text']}), "
              f"red false alarms {s['false_alarms_red']['text']}")
    print(f"wrote {out}")


def cmd_split(args: argparse.Namespace) -> None:
    ids = [line.strip() for line in Path(args.ids).read_text(encoding="utf-8").splitlines() if line.strip()]
    for sid, split in sorted(split_scripts(ids).items()):
        print(f"{sid},{split}")


def cmd_ftc(args: argparse.Namespace) -> None:
    from .ftc import fetch

    sheet = fetch(Path(args.dest))
    print(f"wrote {sheet}")


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

    p = sub.add_parser("labels", help="check a labelling sheet, or write an empty one")
    p.add_argument("path")
    p.add_argument("--template", action="store_true")
    p.set_defaults(func=cmd_labels)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
