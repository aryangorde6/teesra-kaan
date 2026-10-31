# Runbook: from credits to results

Every command below runs from `teesra-kaan/` with the venv. Paid commands need `MODEL_API_KEY` in `.env` and `TEESRAKAAN_ALLOW_PAID=1`. All of them stop at $100 in total, and only while Meta's own meter has been read recently ([spending.md](spending.md)). `teesrakaan budget` says whether paid calls are allowed, and why not.

## 1. When the credits show on Billing (they did on Oct 29)
Read dev.meta.ai → Billing and record what it shows, then make one tiny call:
```bash
.venv/bin/teesrakaan meter --credits-left 150.00 --balance-inr 0 --source "Billing, <time>"
.venv/bin/teesrakaan ping
.venv/bin/teesrakaan budget
```
Then read Billing again, an hour later (recent activity can take that long to appear). The balance must still be ₹0, with the cost taken from the credits. Record the new reading. **After every $10 of spend, paid calls stop until Billing is read and recorded again.** That's how the code knows its own count matches Meta's.

Check the dashboard for a zero-data-retention setting before any donated call is sent (the API reference, read Oct 28, documents no retention setting in the request). While the free credits are in use, Billing says content "may be used for product improvement", so donated calls stay local.

Then one dev re-enactment through `teesrakaan transcribe` and look at the saved events:
- **When do `speaker` events arrive?** Per the schema, a `speaker` event labels the text *since the previous* `speechStart` or `speaker` event, so it can come after the words. If it does, live listening should hold a turn's words until its label arrives (`live.py`), or the first words of a turn are credited to the wrong voice.
- **Pacing:** close code `1008` means the audio arrived slower than real time or ran ahead; `1013` is a rate limit.

## 2. Transcribe each set once (about $0.18 per hour of audio)
Re-enactments are recorded and labelled in `teesrakaan studio` ([recording.md](recording.md)); labels go to `data/labels-in.csv` before any run.
```bash
.venv/bin/teesrakaan transcribe-set data/ftc/audio-dev --out data/transcripts/ftc-dev     # done Oct 30
.venv/bin/teesrakaan transcribe-set data/ftc/audio-test --out data/transcripts/ftc-test   # after the freeze
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

The paraphrase test (10 test scam calls rewritten without the baseline's keywords, evaluation rule v1.4.1), once, after the freeze:
```bash
.venv/bin/teesrakaan transcribe-set data/recordings/paraphrase --out data/transcripts/in-paraphrase
.venv/bin/teesrakaan eval data/transcripts/in-paraphrase --labels data/labels-in.csv --split paraphrase --run A   # then B, C
.venv/bin/teesrakaan keywords data/transcripts/in-paraphrase   # keywords that came back anyway, reported beside the results
.venv/bin/teesrakaan table runs/eval-*/results-paraphrase-*.json   # its own table, never mixed into the test rows
```

The synthetic set (synthetic voices, not people; evaluation rule v1.5), once, after the freeze. The audio was made before it (`eval/synthetic.py`, Kokoro v1.0), so check it first:
```bash
(cd data/synthetic/eval && sha256sum -c ../../../eval/synth-audio.sha256)
.venv/bin/teesrakaan transcribe-set data/synthetic/eval/test --out data/transcripts/synth-test
.venv/bin/teesrakaan transcribe-set data/synthetic/eval/paraphrase --out data/transcripts/synth-paraphrase
.venv/bin/teesrakaan eval data/transcripts/synth-test --labels eval/synth-labels.csv --split test --run A --out runs/eval-synth/results-test-A.json   # then B, C
.venv/bin/teesrakaan eval data/transcripts/synth-paraphrase --labels eval/synth-labels.csv --split paraphrase --run A --out runs/eval-synth/results-paraphrase-A.json   # then B, C
.venv/bin/teesrakaan keywords data/transcripts/synth-paraphrase
.venv/bin/teesrakaan table runs/eval-synth/results-*.json   # rows named IN-synth-…, never mixed with people's recordings
```

Then the table for the README and the video:
```bash
.venv/bin/teesrakaan table runs/eval-*/results-test-*.json
```

## 4. The freeze (Sun Nov 1, 12:00 IST)
```bash
git tag eval-freeze && git log -1 --format='%h %ad' eval-freeze
```
After the tag, prompts, signals, rules, keyword lists, model names and transcription settings don't change for the reported rows. Any fix after it is an extra "after freeze" row.

### After the tag, in this order
1. **A fresh Billing reading first.** Paid calls need one from the last 24 hours and the last $10 of spend (`teesrakaan budget` says which). Read dev.meta.ai → Billing and record it with `teesrakaan meter`. All the runs below cost about $6–8, so one reading should cover them; `budget` says when another is needed.
2. **FTC test labels** in `eval/ftc-test-labels.csv`, from each call's audio and the dataset transcript, committed before any test run (`teesrakaan labels` checks the sheet).
3. **Transcribe** the FTC test calls (`data/ftc/audio-test`), the IN test recordings and their two ablations, and the paraphrase recordings; then check the synthetic set's hashes and transcribe it.
4. **Run** A, B, C and C-no-speakers on each set, and C on the ablation transcripts. Count the keywords in the paraphrase transcripts.
5. **Tables:** one per group (FTC and IN test; paraphrase; synthetic), never mixed. Each test set runs once, and every number goes in as it comes out.
