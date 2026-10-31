"""The FTC labelling sheet for one split, from the dataset's own transcripts (docs/labelling.md; runbook, after the tag).

Every row is English with no pattern or times; what the labeller decides is `ftc_class`: impersonation (poses as a
government body, bank or company and pushes an action), sales (warranty, insurance, solar, debt relief...) or other.
As in the dev sheet, only impersonation calls are scored as scams (`is_scam` 1); sales and other robocalls are
illegal but reported by class, never as false alarms. Test calls are read only after the freeze.

    python eval/ftc_label_sheet.py test                 # each call's id, file and transcript, to label from
    python eval/ftc_label_sheet.py test classes.txt     # writes eval/ftc-test-labels.csv

classes.txt has one line per call: `<call_id> <class> [notes]`. Every call needs one; the sheet is then checked
with `teesrakaan labels`.
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from teesrakaan.ftc import call_id  # noqa: E402
from teesrakaan.labels import COLUMNS, FTC_CLASSES, read_labels, write_template  # noqa: E402

FTC = REPO / "data" / "ftc"


def calls(split: str) -> list[tuple[str, str, str]]:
    """(call id, file name, dataset transcript) for every sampled call in the split, by call id."""
    with open(FTC / "sample.csv", newline="", encoding="utf-8") as f:
        names = [row["file_name"] for row in csv.DictReader(f) if row["split"] == split]
    with open(FTC / "metadata.csv", newline="", encoding="utf-8") as f:
        text = {row["file_name"]: row["transcript"].strip() for row in csv.DictReader(f)}
    return sorted((call_id(n), n, text.get(n, "")) for n in names)


def main() -> None:
    split = sys.argv[1]
    rows = calls(split)
    if len(sys.argv) == 2:
        for n, (cid, name, text) in enumerate(rows, 1):
            print(f"{n}. {cid} {Path(name).name}\n   {text}\n")
        print(f"{len(rows)} {split} calls")
        return
    given = {}
    for line in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines():
        if line.strip():
            cid, cls, *notes = line.split(maxsplit=2)
            given[cid] = (cls, notes[0] if notes else "")
    missing = [cid for cid, _, _ in rows if cid not in given]
    extra = sorted(set(given) - {cid for cid, _, _ in rows})
    wrong = sorted(cid for cid, (cls, _) in given.items() if cls not in FTC_CLASSES)
    if missing or extra or wrong:
        raise SystemExit(f"missing {missing}\nnot in the {split} split {extra}\nclass not one of {FTC_CLASSES}: {wrong}")
    now = datetime.now().astimezone().isoformat(timespec="minutes")
    out = REPO / "eval" / f"ftc-{split}-labels.csv"
    write_template(out, ({
        "call_id": cid, "set": "FTC", "split": split, "is_scam": "1" if given[cid][0] == "impersonation" else "0",
        "pattern": "0", "languages": "en", "ftc_class": given[cid][0], "labeller": "draft", "labelled_at": now,
        "notes": "; ".join(x for x in (Path(name).name, given[cid][1]) if x),
    } for cid, name, _ in rows))
    labels = read_labels(out)
    counts = {c: sum(lab.ftc_class == c for lab in labels.values()) for c in FTC_CLASSES}
    print(f"wrote {out.relative_to(REPO)}: {len(labels)} calls, {counts}; columns {', '.join(COLUMNS)}")


if __name__ == "__main__":
    main()
