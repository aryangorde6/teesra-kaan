# Runbook: from credits to results

Every command below runs from `teesra-kaan/` with the venv. Paid commands need `MODEL_API_KEY` in `.env` and `TEESRAKAAN_ALLOW_PAID=1`. All of them stop at $100 in total, and only while Meta's own meter has been read recently ([spending.md](spending.md)). `teesrakaan budget` says whether paid calls are allowed, and why not.

## 1. When the credits show on Billing (they did on Oct 29)
Read dev.meta.ai → Billing and record what it shows, then make one tiny call:
```bash
.venv/bin/teesrakaan meter --credits-left 150.00 --balance-inr 0 --source "Billing, <time>"
.venv/bin/teesrakaan ping
.venv/bin/teesrakaan budget
```
Then read Billing again. The balance must still be ₹0, with the cost taken from the credits. Record the new reading. **After every $10 of spend, paid calls stop until Billing is read and recorded again.** That's how the code knows its own count matches Meta's.

Check the dashboard for a zero-data-retention setting before any donated call is sent (the API reference, read Oct 28, documents no retention setting in the request). While the free credits are in use, Billing says content "may be used for product improvement", so donated calls stay local.

Then one dev re-enactment through `teesrakaan transcribe` and look at the saved events:
- **When do `speaker` events arrive?** Per the schema, a `speaker` event labels the text *since the previous* `speechStart` or `speaker` event, so it can come after the words. If it does, live listening should hold a turn's words until its label arrives (`live.py`), or the first words of a turn are credited to the wrong voice.
- **Pacing:** close code `1008` means the audio arrived slower than real time or ran ahead; `1013` is a rate limit.

## 2. Transcribe each set once (about $0.18 per hour of audio)
```bash
.venv/bin/teesrakaan transcribe-set data/ftc/audio --out data/transcripts/ftc
.venv/bin/teesrakaan transcribe-set data/recordings/dev --out data/transcripts/in-dev
```
Sessions are saved with every event and its arrival time, so all runs below replay the same transcripts with the real transcription delay. **Test recordings are transcribed only after the freeze** (Sun Nov 1, 12:00).

The transcription ablations are separate transcripts of the test sets:
```bash
.venv/bin/teesrakaan transcribe-set data/recordings/test --out data/transcripts/in-test-nolang --no-language-hint
.venv/bin/teesrakaan transcribe-set data/recordings/test --out data/transcripts/in-test-nokw --no-keywords
```

## 3. Runs (dev before the freeze, test once after it)
| Run | What | Command |
|---|---|---|
| A | keywords + rules (free) | `teesrakaan eval DIR --labels L --split dev --run A` |
| B | Muse Spark free-form, no rules | `… --run B` |
| C | Teesra Kaan: Spark signal questions + rules | `… --run C` |
| C without speaker separation | | `… --run C-no-speakers` |
| C without language hint / keywords | C on the ablation transcripts | `teesrakaan eval data/transcripts/in-test-nolang … --run C` |

Then the table for the README and the video:
```bash
.venv/bin/teesrakaan table runs/eval-*/results-test-*.json
```

## 4. The freeze (Sun Nov 1, 12:00 IST)
```bash
git tag eval-freeze && git log -1 --format='%h %ad' eval-freeze
```
After the tag, prompts, signals, rules, keyword lists, model names and transcription settings don't change for the reported rows. Any fix after it is an extra "after freeze" row.
