"""Every Hindi or Marathi line a person sees or hears, next to its English, for a native speaker to check.

`teesrakaan strings --lang hi` writes one page a reviewer can read on a phone or print: numbered
lines, the spoken warnings first, each with where it appears. Corrections come back by number.
It reads the lines from the code itself (messages.py, report.py and the page's app.js), so the
sheet is never out of step with what the app says.

`--since <commit>` writes an addendum instead: only the lines added or changed since the sheet made
at that commit, numbered on from its last line, so a sheet already sent keeps its numbers.
"""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import messages, report

APP_JS = Path(__file__).parent / "web" / "static" / "app.js"
REPO = Path(__file__).resolve().parents[2]
LANGUAGE = {"hi": ("Hindi", "हिंदी"), "mr": ("Marathi", "मराठी")}

# Where each table's lines appear, most important first: what's spoken aloud, then the warning screen.
WHERE = (
    ("HEADLINE", messages, "The warning's headline: shown big, and spoken aloud"),
    ("ACTION", messages, "What to do now, under the headline: spoken aloud"),
    ("CALLER_SAID", messages, "Above the caller's own words, on the warning"),
    ("SIGNAL_NAME", messages, "The name of a warning sign"),
    ("FACTS", messages, "A fact shown under the warning"),
    ("NEXT_LABEL", messages, "Above the caller's next line"),
    ("NEXT_LINE", messages, "The caller's next line, shown before he says it"),
    ("SCRIPT_LINE", messages, "The caller's next line, in one scam's own words"),
    ("CAME_TRUE", messages, "When the caller says that line"),
    ("FAMILY", messages, "The message sent to family in one tap"),
    ("SCRIPT_NAME", messages, "The name of a scam"),
    ("MATCHES", messages, "Checking a call afterwards"),
    ("COULD_BE", messages, "Checking a call afterwards"),
    ("AHEAD_LABEL", messages, "Checking a call afterwards"),
    ("NOT_ENOUGH", messages, "Checking a call afterwards"),
    ("SCRIPT_DONE", messages, "Checking a call afterwards"),
    ("UI", None, "The page: buttons and messages"),
    ("CALL_NAME", None, "The menu of demo calls: the call's name"),
    ("CALL_LANG", None, "The menu of demo calls: the language spoken in it"),
    ("WHAT_TO_DO", report, "The report for 1930: what to do now"),
    ("TEXT", report, "The report for 1930: its headings"),
    ("RED_ACTION_US", messages, "What to do now, on the US page: spoken aloud"),
)


def _leaves(table, lang: str, path: tuple = ()) -> list[tuple[tuple, str, str]]:
    """(path, English, the language's line) for every line in a table, however it's nested."""
    out = []
    if isinstance(table, dict) and "en" in table and lang in table:
        en, other = table["en"], table[lang]
        if isinstance(en, str):
            return [(path, en, other)]
        if isinstance(en, dict):  # language first, then key: report.TEXT, the page's UI
            return [(path + (k,), en[k], other[k]) for k in en if k in other]
        return [(path + (str(i + 1),), e, o) for i, (e, o) in enumerate(zip(en, other))]  # lists of lines
    if isinstance(table, dict):
        for key, value in table.items():
            out += _leaves(value, lang, path + (str(getattr(key, "name", key)),))
    elif isinstance(table, (tuple, list)):
        for i, value in enumerate(table):
            if isinstance(value, tuple) and len(value) == 3 and isinstance(value[2], dict):  # FACTS: signals, country, lines
                out += _leaves(value[2], lang, path + (value[1], "+".join(sorted(value[0], key=lambda s: int(s[1:])))))
            elif isinstance(value, (dict, tuple, list)):
                out += _leaves(value, lang, path + (str(i + 1),))
    return out


def page_lines() -> dict | None:
    """The page's tables from app.js (UI, and the demo calls' names), with the UI's few sentences that take
    numbers filled with examples. None when node isn't installed."""
    node = shutil.which("node")
    if node is None:
        return None
    script = (
        "const src = require('fs').readFileSync(process.argv[1], 'utf8');"
        "const table = (name) => eval('(' + src.match(new RegExp('const ' + name + ' = (\\\\{[\\\\s\\\\S]*?\\\\n\\\\});'))[1] + ')');"
        "const UI = table('UI'), ui = {};"
        "for (const [lang, t] of Object.entries(UI)) {"
        "  ui[lang] = {};"
        "  for (const [k, v] of Object.entries(t)) ui[lang][k] = typeof v === 'function' ? v(2, 30) : v;"
        "}"
        # The menu's tables are keyed by call (or spoken language) first: turn them language first, like UI.
        "const byLang = (t) => { const o = {};"
        "  for (const [k, v] of Object.entries(t)) for (const [lang, s] of Object.entries(v)) (o[lang] ||= {})[k] = s;"
        "  return o; };"
        "console.log(JSON.stringify({UI: ui, CALL_NAME: byLang(table('CALL_NAME')), CALL_LANG: byLang(table('CALL_LANG'))}));"
    )
    done = subprocess.run([node, "-e", script, str(APP_JS)], check=True, capture_output=True, text=True)
    return json.loads(done.stdout)


def collect(lang: str) -> list[dict]:
    """The numbered lines for one language, in the order a reviewer should check them."""
    page = page_lines()
    out = []
    for name, module, where in WHERE:
        table = (page or {}).get(name) if module is None else getattr(module, name)
        if table is None:
            continue
        for path, en, other in _leaves(table, lang):
            us = name in ("RED_ACTION_US",) or "US" in path
            out.append({"n": len(out) + 1, "table": name, "key": ".".join(path), "where": where + (" (US page)" if us else ""),
                        "en": en, "text": other, "spoken": name in ("HEADLINE", "ACTION", "RED_ACTION_US"), "us": us})
    # The US page's lines last: India's are the ones that matter first.
    out.sort(key=lambda line: line["us"])
    for i, line in enumerate(out, 1):
        line["n"] = i
    return out


def collect_at(commit: str, lang: str) -> list[dict]:
    """collect() as the code stood at an earlier commit: the sheet a reviewer may already have."""
    archive = subprocess.run(["git", "-C", str(REPO), "archive", commit, "src"], check=True, capture_output=True).stdout
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["tar", "-x", "-C", tmp], input=archive, check=True)
        done = subprocess.run([sys.executable, "-c", f"import json, teesrakaan.strings as s; print(json.dumps(s.collect({lang!r})))"],
                              env={**os.environ, "PYTHONPATH": str(Path(tmp) / "src")}, check=True, capture_output=True, text=True)
    return json.loads(done.stdout)


def collect_since(commit: str, lang: str) -> tuple[list[dict], int]:
    """The lines added or changed since the sheet made at `commit`, numbered on from its last line, and that
    sheet's length. A changed line says which old number it replaces."""
    old = collect_at(commit, lang)
    before = {(line["table"], line["key"]): line for line in old}
    out = []
    for line in collect(lang):
        prev = before.get((line["table"], line["key"]))
        if prev and (prev["en"], prev["text"]) == (line["en"], line["text"]):
            continue
        out.append({**line, "n": len(old) + len(out) + 1, "replaces": prev["n"] if prev else None})
    return out, len(old)


def to_html(lang: str, version: str, since: str | None = None) -> str:
    """One page, phone-sized and printable; with `since`, the addendum to the sheet made at that commit."""
    name, native = LANGUAGE[lang]
    if since:
        lines, sent = collect_since(since, lang)
        span = f"lines {sent + 1}–{sent + len(lines)}" if lines else "no lines"
        intro = (f'<p><b>An addendum</b> to the sheet of {sent} lines from commit {html.escape(since)}: only the {len(lines)} '
                 f"lines added or changed since, numbered on from it ({span}), so its numbers still hold. A changed line "
                 "says which line it replaces; check it here, not there.</p>")
    else:
        lines, intro = collect(lang), ""
    spoken = [line["n"] for line in lines if line["spoken"] and not line["us"]]
    items = []
    for line in lines:
        cls = "item spoken" if line["spoken"] else "item"
        replaces = f' · replaces line {line["replaces"]}' if line.get("replaces") else ""
        items.append(
            f'<li class="{cls}"><div class="meta"><b>{line["n"]}</b> · {html.escape(line["where"])}{replaces}'
            f'<span class="key">{html.escape(line["table"])} {html.escape(line["key"])}</span></div>'
            f'<p class="en">{html.escape(line["en"])}</p>'
            f'<p class="text" lang="{lang}">{html.escape(line["text"])}</p>'
            '<p class="answer">☐ OK &nbsp; Better: ______________________________________</p></li>')
    most = (f"<p><b>Most important: lines {spoken[0]}–{spoken[-1]}</b> (red edge). They are spoken aloud the moment a "
            "call looks like a scam, so they must be short, clear and calm.</p>") if spoken else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Teesra Kaan: {name} check</title>
<style>
  body {{ margin: 0 auto; max-width: 760px; padding: 16px; font-family: "Noto Sans", "Noto Sans Devanagari", sans-serif;
         color: #161311; background: #f2e8d0; line-height: 1.45; }}
  h1 {{ font-size: 1.4rem; margin: 0 0 4px; }}
  .how {{ background: #fff; border-left: 6px solid #f5b400; padding: 10px 14px; margin: 12px 0 18px; }}
  .how p {{ margin: 4px 0; }}
  ol {{ list-style: none; padding: 0; margin: 0; }}
  .item {{ background: #fff; border-radius: 8px; padding: 10px 14px; margin: 0 0 10px; break-inside: avoid; }}
  .item.spoken {{ border-left: 6px solid #c8261e; }}
  .meta {{ font-size: 0.85rem; color: #5a5148; }}
  .key {{ float: right; font-family: monospace; font-size: 0.75rem; color: #8a8178; }}
  .en {{ margin: 6px 0 2px; color: #5a5148; }}
  .text {{ margin: 2px 0 6px; font-family: "Noto Sans Devanagari", sans-serif; font-size: 1.25rem; }}
  .answer {{ margin: 0; font-size: 0.85rem; color: #8a8178; }}
  @page {{ margin: 12mm; }}
  @media print {{
    body {{ background: #fff; max-width: none; padding: 0; font-size: 10pt; }}
    .how {{ border: 1px solid #ccc; border-left-width: 6px; }}
    .item {{ border: 1px solid #ccc; padding: 4px 10px; margin: 0 0 4px; }}
    .key {{ display: none; }}
    .en {{ margin: 2px 0 0; }}
    .text {{ font-size: 12.5pt; margin: 0 0 2px; }}
  }}
</style></head>
<body>
<h1>Teesra Kaan · {name} ({native}) language check{" · addendum" if since else ""}</h1>
<p class="meta">{len(lines)} lines · from the app's code at {html.escape(version)}</p>
<div class="how">
{intro}<p><b>What this is:</b> Teesra Kaan listens to a phone call on speaker and warns the person, in their language, when the caller sounds like a scammer. Every {name} line it shows or says is below, under its English.</p>
<p><b>For each line:</b> is it correct, and does it sound natural, the way a person in the family would say it to an older relative? If yes, tick OK. If not, write the better wording.</p>
{most}
<p>Words in {{curly brackets}} are filled in by the app: keep them as they are. The US page's lines come last and matter least.</p>
<p><b>Send back</b> only the lines to change, by number, e.g. "7: …". A photo of the marked page works too.</p>
</div>
<ol>
{chr(10).join(items)}
</ol>
</body></html>
"""
