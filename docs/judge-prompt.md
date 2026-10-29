# The Muse Spark judge: prompt v1

Version 1, Oct 28, 2026. **Drafted before any call to the API.** The prompt text lives in [`src/teesrakaan/judge.py`](../src/teesrakaan/judge.py) (`SPARK_SYSTEM_V1`, `SPARK_SCHEMA_V1`), so the code and this note can't drift apart. Changes after Nov 1, 12:00 IST are "after freeze" (see [evaluation-rule.md](evaluation-rule.md)).

## What Spark is asked to do
After each caller turn, and every 6 s inside a long one, Spark gets:
- **the system prompt:** it's a listener beside the person who got the call; it answers fixed questions about the CALLER only; it never decides "scam or not";
- **the transcript so far,** as `CALLER:` and `YOU:` lines, in whatever script the transcriber produced;
- **only the questions still open.** A signal already found stays found, so it isn't asked again, and the prompt gets shorter as the call goes on.

It replies with JSON that lists only the "yes" answers, each with a quote:
```json
{"yes": [{"id": "A1", "quote": "main Mumbai crime branch se Inspector Sharma bol raha hoon"}]}
```

## Why it's built this way
- **The model answers, the rules decide.** Spark is good at "did the caller ask for an OTP, in any language or wording?" and shouldn't be trusted with "is this a scam?". The rules in [`signals.py`](../src/teesrakaan/signals.py) are short enough to print on the screen.
- **Every "yes" must quote the caller,** and the code checks the quote against the caller's own words before it counts ([`listener.py`](../src/teesrakaan/listener.py)). A quote that isn't there, or that only the listener said, is dropped and logged. So a warning can always show the exact words, with the second they were said, and a hallucinated reason can't raise an alarm.
- **Listing only "yes" answers** keeps the output to a few dozen tokens, which keeps latency and cost down.
- **Negation is called out** in the prompt ("we never ask for your OTP" isn't asking), because it's exactly where the keyword baseline fails (see the test `test_keyword_baseline_is_fooled_by_negation`).
- **No translation.** Quotes stay in the original script, so the check against the transcript is exact, and the warning shows the caller's real words.

## Settings for the first real calls (Oct 30, after the credits land)
- Model `muse-spark-1.3`, **not** the contributor tier (donated calls must not be used for training).
- **Zero data retention:** the speech-to-text docs (read Oct 28) give it the same price but no request parameter, so it's probably an account or key setting. Check the dashboard before the first donated call is sent; until it's confirmed on, donated calls stay local.
- JSON-schema output with `SPARK_SCHEMA_V1`; `reasoning_effort` minimal or low, picked on dev by latency.
- The system prompt and the question list form a fixed prefix, so cached input ($0.15/M instead of $1.25/M) should apply to most of each request. Check that the usage figures show it.
- The $100 hard stop is enforced in code before every call, and checked against Meta's own meter ([spending.md](spending.md)).

## Expected cost (offline estimate, keyword judge sized as Spark)
`teesrakaan simulate` counts the tokens Spark would get for the same checks:

| Demo call | Length | Judge calls | Input tokens | Estimated cost |
|---|---|---|---|---|
| digital arrest (Hinglish) | 76 s | 14 | ~14,000 | ~$0.024 |
| TRAI, press 9 (Marathi) | 33 s | 6 | ~5,800 | ~$0.010 |

About $0.02 a minute before caching, rising on long calls because the transcript grows. For the evaluation (about 70 IN calls and 200 FTC calls, run once each for comparison C, B and three ablations) that's roughly $30–50, inside the $100 stop. Real numbers replace these after the first run.

## First checks on dev (not test)
1. 5 dev calls: does every "yes" quote pass the check? Count rejected quotes.
2. Latency per call: median and p90. If p90 is above 3 s, try a lower `reasoning_effort` or a shorter window.
3. The two hard negatives in `examples/calls/` must not go red.

## The clients (written Oct 28, tested against fakes, never called)
- [`spark.py`](../src/teesrakaan/spark.py): Chat Completions to `https://api.meta.ai/v1`, JSON-schema output, no automatic retries, every call reserved and settled in the $100 ledger, replies cached on disk with their original latency, the contributor tier refused in code.
- [`asr.py`](../src/teesrakaan/asr.py): the realtime WebSocket (`wss://api.meta.ai/v1/asr/realtime`, `muse-voice-transcribe-1.0`, `PCM_16KHZ`, `DIARIZATION`, cumulative partials, language bias Hindi/Marathi/English, keyword biasing). Audio is paced at real time in 100 ms frames; every event is saved with the second it arrived. A saved session becomes a call whose words carry both the time said (the server's audio clock) and the time heard (arrival), so replays keep the real transcription delay.
- **Which voice is the caller:** speaker separation only says "A" and "B". The listener treats whoever has said the most so far as the caller, using only what's been heard up to that moment.
- **Paid calls are off** unless `TEESRAKAAN_ALLOW_PAID=1`. First check on Oct 30: `teesrakaan ping`, then `teesrakaan budget`, then confirm on dev.meta.ai Billing that the cost came off the credits.
