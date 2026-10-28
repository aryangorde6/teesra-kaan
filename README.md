# Teesra Kaan — the third ear on a scam call

On a scam call there are two people: the caller, and someone being frightened into paying. **Teesra Kaan** ("the third ear") is a third listener. Put the call on speaker and open the page. It listens in Hindi, Marathi or English. The moment the caller starts a known scam (a fake police "digital arrest", a KYC or bank call, "your number will be blocked", an OTP request), it warns you in your language, quoting the caller's own words, and tells you what to do: hang up, and call 1930. After the call, it prepares what you need for a report on cybercrime.gov.in.

Built for the Meta Global AI Developer Hackathon (Oct 26 – Nov 4, 2026) with Meta's Muse Voice Transcribe and Muse Spark.

**Status:** in development. The offline core runs and is tested; the Meta API clients and the live page come next.
- [What it listens for](docs/scam-tactics.md): 12 signals, the alarm rules, 9 scam patterns with official sources
- [How it's tested](docs/evaluation-rule.md), written before any results
- [The Muse Spark prompt](docs/judge-prompt.md) and [the labelling sheet](docs/labelling.md)

## How it decides
1. **Muse Voice Transcribe** turns the call into text as it happens, keeping the caller and you apart.
2. **Muse Spark** answers 12 fixed yes/no questions about what the caller has said ("Claims to be police?", "Asks for an OTP?", "Tells you not to tell anyone?"), quoting the caller for every yes.
3. **The code checks every quote** against the caller's actual words, and drops any it can't find.
4. **Fixed rules, not the model, raise the alarm:** two signals make a warning; if one of them is an ask for money, secrets, an app or a PIN, it's red.

## Try the offline core
No API key needed: a keyword judge stands in for Muse Spark.

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e . pytest
.venv/bin/teesrakaan simulate examples/calls/demo-digital-arrest.json --lang hi --realtime
.venv/bin/teesrakaan report examples/calls/demo-digital-arrest.json
.venv/bin/python -m pytest
```

The calls in `examples/calls/` are written demo scripts, not real calls; every name, number and ID in them is made up.

## Layout
| File | What it does |
|---|---|
| `src/teesrakaan/signals.py` | The 12 signal questions and the alarm rules |
| `src/teesrakaan/transcript.py` | Calls, turns, and the transcript heard so far; maps a quote to the second it was said |
| `src/teesrakaan/judge.py` | The judge interface, the Muse Spark prompt v1 and its reply parser |
| `src/teesrakaan/keywords.py` | The keyword judge: offline stand-in and comparison A |
| `src/teesrakaan/listener.py` | Hears the call, asks the judge, checks quotes, keeps the alarm. The same code runs live and in the evaluation |
| `src/teesrakaan/simulate.py` | Plays a call to the listener with transcription and model delays |
| `src/teesrakaan/metrics.py` | Caught, false alarms, time to warning, warned before the ask, with Wilson 95% intervals |
| `src/teesrakaan/report.py` | The report pack for 1930 and cybercrime.gov.in |
| `src/teesrakaan/messages.py` | Warnings in English, Hindi and Marathi |
| `src/teesrakaan/labels.py` | The labelling sheet and the fixed dev/test splits |

## Licence
MIT
