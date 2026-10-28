# Teesra Kaan — the third ear on a scam call

**Put a suspicious call on speaker and open the page. Teesra Kaan listens in Hindi, Marathi or English, and the moment the caller starts a known scam it warns you in your language, quoting the caller's own words. When the call ends, it hands you a ready report for 1930 and cybercrime.gov.in.**

<img src="docs/demo.gif" width="300" align="right" alt="The page playing a demo 'digital arrest' call: the transcript, then a red warning in Hindi quoting the caller">

*Right: the page playing a written demo call (4× speed, offline keyword stand-in for Muse Spark). It will be replaced by a real re-enacted call through Muse Voice Transcribe and Muse Spark.*

- **Live:** https://teesrakaan.aryangorde.com *(from Nov 2)*
- **Video (3 min):** *(link on Nov 4)*
- **Built during** the Meta Global AI Developer Hackathon, Oct 26 – Nov 4, 2026. Every commit in this repo is from those dates.

## Why
In 2024 Indians lost ₹1,935.51 crore to "digital arrest" calls alone, and ₹22,845.73 crore to cyber fraud overall (Ministry of Home Affairs replies in Parliament; sources in [docs/figures.md](docs/figures.md)). The script is always the same: a "police" or "bank" caller, a threat, "don't tell anyone", then an ask for money or an OTP. Caller ID flags numbers; nothing listens to what is being said, in the language it's said in.

## How it decides
| Step | Meta model | What it does |
|---|---|---|
| 1. Hear | **Muse Voice Transcribe** (realtime, speaker separation, Hindi/Marathi/English bias, scam-term keyword biasing) | Writes the call down as it happens and keeps the two voices apart |
| 2. Ask | **Muse Spark 1.3** (JSON-schema output) | After each thing the caller says, answers 12 fixed yes/no questions about the caller ("claims to be police?", "asks for an OTP?", "says don't tell family?"), quoting the caller's exact words for every yes |
| 3. Check | — | Every quote is matched against what the caller actually said; a quote that isn't there is thrown away, so a made-up reason can't raise an alarm |
| 4. Decide | — | Fixed rules, not the model: two warning signs give a warning; if one is an ask for money, an OTP or PIN, an app or a link, it's red. One sign alone never warns |
| 5. Report | — | At hang-up: the caller's claims with quotes and times, every amount, number and UPI ID mentioned, and what to do next |

The questions, rules and the scam patterns they come from (with official sources) are in [docs/scam-tactics.md](docs/scam-tactics.md).

## Does it work?
*The frozen test run is on Sun Nov 1, 12:00 IST; its numbers go here exactly as they come out.* The test was fixed before any result existed: [docs/evaluation-rule.md](docs/evaluation-rule.md).

| Set | What it is |
|---|---|
| **FTC** | 200 real US scam robocalls from the FTC's Project Point of No Entry (public domain), 50 dev / 150 test |
| **IN-scam / IN-genuine** | 40 scam and 30 genuine calls in Hindi, Marathi, English and Hinglish, re-enacted from police, RBI and NPCI advisories, recorded on speakerphone (28 dev / 42 test) |
| **IN-real** | Real scam calls donated by Indian families with written consent (private; numbers only) |

Compared on the same test: **A** keyword lists + the same rules, **B** Muse Spark asked "is this a scam?", **C** Teesra Kaan, plus C without speaker separation, language hint or keyword biasing. Every number in the video comes from `teesrakaan table` on that run. Development steps and their dev-set numbers are logged in [docs/dev-log.md](docs/dev-log.md).

## Try it
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e '.[web]' pytest
.venv/bin/teesrakaan serve            # open http://127.0.0.1:8000 and play a demo call
.venv/bin/python -m pytest            # 100+ tests, no network, no key
```
Live listening and the Meta-model runs need `MODEL_API_KEY` in `.env` and `TEESRAKAAN_ALLOW_PAID=1`; every paid call goes through a ledger that stops at $120. The full sequence is in [docs/runbook.md](docs/runbook.md).

The demo calls in `examples/calls/` are written scripts, not real calls; every name, number and ID in them is made up.

## Limits (honest)
- The Indian test calls are re-enactments; the FTC calls are real but American and in English. Real donated calls are few. Each set is reported separately, with 95% intervals.
- Speaker separation labels voices "A" and "B"; the caller is taken to be whoever has said the most so far, which can be wrong in the first seconds.
- It needs the call on speaker, near the phone or laptop running the page. It doesn't intercept calls.
- A warning is advice, not a verdict. The genuine-call set measures how often it warns when it shouldn't.

## Layout
| File | What it does |
|---|---|
| `src/teesrakaan/signals.py` | The 12 signal questions and the alarm rules |
| `src/teesrakaan/listener.py` | Hears the call, asks the judge, checks quotes, keeps the alarm. The same code runs live and in the evaluation |
| `src/teesrakaan/judge.py`, `keywords.py` | The Muse Spark prompt and parser; the keyword baseline |
| `src/teesrakaan/spark.py`, `asr.py`, `budget.py` | Muse Spark and Muse Voice Transcribe clients, behind a $120 hard stop |
| `src/teesrakaan/live.py`, `web/` | Live listening and the page |
| `src/teesrakaan/simulate.py`, `metrics.py`, `labels.py` | Replays calls with real delays; Wilson 95% intervals; the labelling sheet and fixed splits |
| `src/teesrakaan/report.py`, `messages.py` | The 1930 report and the warnings, in English, Hindi and Marathi |
| `eval/` | Re-enactment scripts, their split, FTC dev labels |
| `deploy/` | The server setup for the live page |

## Licence
MIT. The FTC recordings are public domain (NCSU Robocall Audio Dataset); they're fetched by `teesrakaan ftc-fetch`, not stored here.
