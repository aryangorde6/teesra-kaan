# Runbook: from credits to results

Every command below runs from `teesra-kaan/` with the venv. Paid commands need `MODEL_API_KEY` in `.env` and `TEESRAKAAN_ALLOW_PAID=1`; all of them stop at $120 in total (`teesrakaan budget`).

## 1. When the credits show on Billing (Oct 30)
```bash
.venv/bin/teesrakaan ping
.venv/bin/teesrakaan budget
```
Then check on dev.meta.ai → Billing that the cost came off the credits, not the card. Check the dashboard for a zero-data-retention setting before any donated call is sent.

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
