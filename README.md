# Teesra Kaan — the third ear on a scam call

**Put a suspicious call on speaker and open the page. Teesra Kaan listens in Hindi, Marathi or English, and the moment the caller starts a known scam it warns you in your language, quoting the caller's own words. Then it shows you the caller's next line before they say it, and ticks it off in their own words when they do. When the call ends, it hands you a ready report for 1930 and cybercrime.gov.in.**

<img src="docs/demo.gif" width="300" align="right" alt="The page playing a demo 'digital arrest' call: the transcript, then a red warning in Hindi quoting the caller">

*Right: the page playing a written demo call (4× speed, offline keyword stand-in for Muse Spark). It will be replaced by a real re-enacted call through Muse Voice Transcribe and Muse Spark.*

- **Live:** https://teesrakaan.aryangorde.com *(from Nov 2)*
- **Video (3 min):** *(link on Nov 4)*
- **Built during** the Meta Global AI Developer Hackathon, Oct 26 – Nov 4, 2026. Every commit in this repo is from those dates. One module is adapted from code written earlier in the same event: the spending ledger in `src/teesrakaan/budget.py` comes from this hackathon's first project, Double Take (Oct 27, 2026). The project changed after the application; the submission says so.

## Why
In 2024 Indians lost ₹1,935.51 crore to "digital arrest" calls alone, and ₹22,845.73 crore to cyber fraud overall (Ministry of Home Affairs replies in Parliament; sources in [docs/figures.md](docs/figures.md)). The script is always the same: a "police" or "bank" caller, a threat, "don't tell anyone", then an ask for money or an OTP. Caller ID flags numbers; nothing listens to what is being said, in the language it's said in.

The script isn't only Indian. Americans reported losing $3.5 billion to impostor scams in 2025, about $920 million of it to government impersonators (FTC). So Teesra Kaan is built for India's scam calls and tested on America's too: the frozen test includes 150 real US scam robocalls.

## The next line
A warning often loses to fear. In October 2026 a retired doctor in Gujarat sent ₹58.5 lakh to "digital arrest" callers even after her bank warned her ([DeshGujarat](https://deshgujarat.com/2026/10/02/despite-bank-warning-doctor-gripped-by-fear-transfers-%e2%82%b958-50-lakh-in-digital-arrest-scam/)). What a frightened person can't argue with is proof that the caller is reading from a script, and a field experiment found that forewarning people about a specific scam made them less likely to fall for it ([Scheibe et al., 2014](https://longevity.stanford.edu/forewarning-reduces-fraud-susceptibility-in-vulnerable-consumers)).

So Teesra Kaan says the caller's next line before they say it. The nine scam patterns in [docs/scam-tactics.md](docs/scam-tactics.md) are written in [`playbook.py`](src/teesrakaan/playbook.py) as ordered steps, taken from the police, RBI and DoT advisories. Once two steps of a script have been heard, the page shows the next one:

> **Next line in this scam's script:** "Don't tell anyone. Don't hang up."

When the caller says it, the line is ticked: *"The caller just said it: “kisi ko mat batana…”. This call is following a scam script."*

- **Fixed scripts make the prediction, not a model.** It predicts only when every script that fits the call so far names the same next step. After "police" and "FIR" alone, the call could be a digital arrest or a KYC call, so it waits.
- **A line counts only if the caller says it after it was shown.** A line said earlier but recognised late doesn't count.
- **It's measured, not just demonstrated.** The frozen test reports how often the shown lines came true, against a naive guess made at the same moments; how many seconds ahead they were; on how many scam calls one was shown; and how many were shown on genuine calls (metric 7 in [docs/evaluation-rule.md](docs/evaluation-rule.md)). FTC robocalls usually end at "press 1", before the ask, so few lines will come true there.

## How it decides
| Step | Meta model | What it does |
|---|---|---|
| 1. Hear | **Muse Voice Transcribe** (realtime, speaker separation, Hindi/Marathi/English bias, scam-term keyword biasing) | Writes the call down as it happens and keeps the two voices apart |
| 2. Ask | **Muse Spark 1.3** (JSON-schema output) | After each thing the caller says, answers 12 fixed yes/no questions about the caller ("claims to be police?", "asks for an OTP?", "says don't tell family?"), quoting the caller's exact words for every yes |
| 3. Check | — | Every quote is matched against what the caller actually said; a quote that isn't there is thrown away, so a made-up reason can't raise an alarm |
| 4. Decide | — | Fixed rules, not the model: two warning signs give a warning; if one is an ask for money, an OTP or PIN, an app or a link, it's red. One sign alone never warns |
| 5. Predict | — | The signs so far are matched against the nine scam scripts; when they agree on the next step, the page shows the caller's next line, and ticks it when it's said |
| 6. Report | — | At hang-up: the caller's claims with quotes and times, every amount, number and UPI ID mentioned, and what to do next |

The questions, rules and the scam patterns they come from (with official sources) are in [docs/scam-tactics.md](docs/scam-tactics.md).

## Does it work?
*The frozen test run is on Sun Nov 1, 12:00 IST; its numbers go here exactly as they come out.* The test was fixed before any result existed: [docs/evaluation-rule.md](docs/evaluation-rule.md).

| Set | What it is |
|---|---|
| **FTC** | 200 real US scam robocalls from the FTC's Project Point of No Entry (public domain), 50 dev / 150 test |
| **IN-scam / IN-genuine** | 40 scam and 30 genuine calls in Hindi, Marathi, English and Hinglish, re-enacted from police, RBI and NPCI advisories, recorded on speakerphone (28 dev / 42 test) |
| **IN-real** | Real scam calls donated by Indian families with written consent (private; numbers only) |

Compared on the same test: **A** keyword lists + the same rules, **B** Muse Spark asked "is this a scam?", **C** Teesra Kaan, plus C without speaker separation, language hint or keyword biasing. Every number in the video comes from `teesrakaan table` on that run. Development steps and their dev-set numbers are logged in [docs/dev-log.md](docs/dev-log.md).

## What already exists
AI that spots scam calls is not new. This is what we found, and how Teesra Kaan differs.

| What | What it does |
|---|---|
| [Google Scam Detection](https://blog.google/security/new-ai-powered-scam-detection-features/) | On-device warnings during calls in Google's own Phone app, on Pixel phones. In India since Nov 2025 in Hindi and English ([TechCrunch](https://techcrunch.com/2025/11/20/google-steps-up-ai-scam-protection-in-india-but-gaps-remain)); off by default ([Techlicious](https://www.techlicious.com/blog/new-google-scam-call-and-text-warning/)); on Galaxy S26 phones in 2026 ([TechRepublic](https://www.techrepublic.com/article/news-google-gemini-scam-detection-android-samsung-expansion/)) |
| [Hiya AI Phone](https://www.helpnetsecurity.com/2025/01/28/hiya-ai-phone/) | Screens unknown callers, and analyses call audio in real time for scam language and AI voices |
| [Savi](https://letsdatascience.com/news/savi-launches-app-to-block-ai-scams-e87998af) (Jul 2026) | Screens calls, texts and voicemail for AI scams, with live-call monitoring |
| [Truecaller Family Protection](https://techcrunch.com/2026/03/12/truecallers-now-lets-you-hang-up-on-scammers-on-behalf-of-your-family/) (India, Mar 2026) | Lets a family member hang up a scam call for someone else |
| Hackathon projects: [ShaScam](https://devpost.com/software/shascam), [Call Cop](https://devfolio.co/projects/call-cop-f7a1), [a FOSS Hack 25 entry](https://fossunited.org/hack/fosshack25/p/b7vum5on5h), [Guardian Angel](https://portland.aitinkerers.org/hackathons/h_Xu4dbx3kfMs/entries/ht_59nCFqZrOQQ) | Live scam-call detection |
| [ScriptMind](https://arxiv.org/abs/2601.13581) (EACL 2026 Industry Track) | Research: an 11B model fine-tuned on 571 Korean phone-scam cases infers the scam's script and predicts the scammer's next utterance |
| [PreScam](https://arxiv.org/abs/2605.12243) (May 2026) | Research: a benchmark built from real scam reports; it found that "next-action prediction remains only moderately successful even for strong LLMs" |

**How Teesra Kaan differs:**
- **The next line, live, in Hindi, Marathi and English.** The two papers predict the scammer's next move in research settings; neither runs live on a call or in an Indian language. Ours comes from fixed scripts out of the advisories, not from a model, which is where PreScam found models weak.
- **It shows its proof.** Every warning quotes the caller's own words, and a quote the caller never said is thrown away.
- **Fixed rules decide, not the model,** and one warning sign alone never warns.
- **It's measured** on a test fixed before any result, on real FTC calls and Indian re-enactments, against keyword lists and against Muse Spark asked plainly "is this a scam?".
- **It works with any call app,** because it listens through the speaker. Digital-arrest callers move people to WhatsApp and Skype video calls, outside a phone maker's own dialer.

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
- The next line knows only the nine scripts. A new script, or one played in an unusual order, gets no prediction or a wrong one; the test counts both.

## Layout
| File | What it does |
|---|---|
| `src/teesrakaan/signals.py` | The 12 signal questions and the alarm rules |
| `src/teesrakaan/playbook.py` | The nine scam scripts as ordered steps, and the next line they predict |
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
