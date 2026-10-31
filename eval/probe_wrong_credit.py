"""A probe, not a dev or test call: the "sent extra by mistake" scam that cost an elder Aryan spoke to ₹20,000
(docs/dev-log.md, Oct 31, 20:17), written fresh from his description in Hinglish and English, with made-up names.
Shows the warning, the signals and which script the playbook matched. Never in a reported row.

    python eval/probe_wrong_credit.py A C     # C is PAID (Muse Spark), cents; cached after the first run
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from teesrakaan.cli import _run  # noqa: E402
from teesrakaan.playbook import ahead  # noqa: E402
from teesrakaan.scripts import to_call  # noqa: E402
from teesrakaan.simulate import Timing, simulate  # noqa: E402

CALLS = [
    {"id": "probe-wrong-credit-hi", "set": "IN-scam", "pattern": 0, "language": "hi+en", "lines": [
        ["caller", "Namaste uncle, main Ramesh bol raha hoon, Suresh bhaiya ka dost. Bhaiya ne kaha tha aapko pachees hazaar bhejne hain."],
        ["listener", "Achha, haan, Suresh ne bataya tha shayad."],
        ["caller", "Main abhi Google Pay se bhej raha hoon, aapke phone pe message aa jayega."],
        ["listener", "Theek hai."],
        ["caller", "Uncle, message aaya? Galti se pachees ki jagah paintalees hazaar chale gaye, mera haath galat jagah dab gaya."],
        ["listener", "Haan, message mein paintalees hazaar likha hai."],
        ["caller", "Uncle please baaki ke bees hazaar isi number pe wapas bhej dijiye, mujhe abhi hospital mein jama karne hain, jaldi kijiye."],
        ["listener", "Achha, bhejta hoon."],
    ]},
    {"id": "probe-wrong-credit-en", "set": "IN-scam", "pattern": 0, "language": "en", "lines": [
        ["caller", "Hello uncle, this is Ramesh, Suresh's friend. Suresh asked me to send you twenty-five thousand."],
        ["listener", "Oh, yes, he may have mentioned it."],
        ["caller", "I'm sending it on Google Pay right now, you'll get a message on your phone."],
        ["listener", "Okay."],
        ["caller", "Uncle, did the message come? I've sent forty-five thousand instead of twenty-five, my finger slipped."],
        ["listener", "Yes, the message says forty-five thousand."],
        ["caller", "Please send the extra twenty thousand back to this same number, I have to pay it at the hospital right now, please hurry."],
        ["listener", "Okay, I'll send it."],
    ]},
]

for run in sys.argv[1:]:
    judge, options, _ = _run(run)
    for s in CALLS:
        call = to_call(s)
        r = simulate(call, judge, Timing(), **options)
        ask = call.turns[6]
        L = r.listener
        seen = [f.id for f in sorted(L.found.values(), key=lambda f: f.said_at)]
        a = ahead(seen)
        print(f"{run} {s['id']}: level {int(r.level)}, t_warn {r.t_warn}, the ask {ask.start}-{ask.end} s, signals {seen}")
        for f in L.found.values():
            print(f"    {f.id}: {f.quote!r}")
        print(f"    scripts {a.scripts if a else None}, ahead {a.steps if a else None}")
        print(f"    predictions {[(p.step, p.came_true) for p in L.predictions]}")
