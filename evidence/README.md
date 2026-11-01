# The frozen test run, replayable

Everything the one test run saved (Nov 1, 2026, 12:02–12:29 IST, on the commit tagged `eval-freeze`, by [eval/after_freeze.sh](../eval/after_freeze.sh)), so every number in the README can be checked without a key:

- **`transcripts/`**: each test call's session from Muse Voice Transcribe, with every event and the time it arrived: the 150 FTC test robocalls (`ftc-test`), the 33 synthetic Indian test calls, 18 scam and 15 genuine (`synth-test`), and the 9 rewritten without a keyword (`synth-paraphrase`).
- **`spark-replies/`**: the 573 Muse Spark replies the run used, filed by question as [spark.py](../src/teesrakaan/spark.py) saved them.
- **`results/`**: each run's outcome for every call (`teesrakaan eval`), the tables in the README (`teesrakaan table`), the keyword check of the rewritten calls, and the run's log.

Replay it, offline, in a few seconds:
```bash
.venv/bin/python eval/replay_frozen.py
```
It runs every comparison again through the same code, with the saved replies in place of the API (a missing one stops it; nothing calls the API), checks each call's outcome against `results/`, and prints the tables, which must match the saved ones exactly.

It allows for two things:
- **The keyword runs (A) time their own judge by the clock**, so a busy machine moves their times by milliseconds. Times are compared to 0.25 s; the tables exactly.
- **One FTC call under C, `ftc-0b89b1bb64`.** In the run, one of its Muse Spark replies hit the output limit; the reply couldn't be read, so that check found nothing, and a reply cut off there is never saved. The same question (the call has one voice, so it's the same with speakers merged) was answered in full and saved ten minutes later, in the C-no-speakers run. Replayed with that reply, the call is still amber, 2.7 s earlier. No number in the tables changes.

Not here: the audio. The FTC calls are fetched by `teesrakaan ftc-fetch` (public domain), and the synthetic calls are made by [eval/synthetic.py](../eval/synthetic.py), checked against [eval/synth-audio.sha256](../eval/synth-audio.sha256). The one call re-enacted with real voices was outside the test and stays private.
