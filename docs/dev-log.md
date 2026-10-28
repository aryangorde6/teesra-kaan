# Development log

Every change to the signals, rules, keyword lists or the Spark prompt, with the **dev** numbers before and after. Test sets are never used here. Dev numbers are optimistic by construction, because the changes were made by looking at these same calls; only the frozen test run counts.

## Oct 28, 2026, 19:50 IST: FTC dev, keyword baseline, rules v1.1 → v1.2
- **Set:** the 50 FTC dev calls (41 impersonation, 8 sales, 1 other; draft class labels in [`eval/ftc-dev-labels.csv`](../eval/ftc-dev-labels.csv), to be spot-checked by Aryan).
- **Input:** the dataset's own transcripts, words spread evenly over each recording. The real run uses Muse Voice Transcribe on the audio.
- **Judge:** keywords (comparison A). Muse Spark hasn't been called yet.

| Version | Impersonation warned | Impersonation red | Sales warned |
|---|---|---|---|
| v1.1 | 24/41 (43–72%) | 0/41 | 5/8 |
| v1.2 | 40/41 (87–100%) | 0/41 | 6/8 |

- **What changed:** see "Changes" in [scam-tactics.md](scam-tactics.md). In short, A1 covers companies, A2 covers "suspicious activity / unauthorized order", A3 covers "as soon as possible", A12 covers "you qualify for".
- **Why red is 0:** these robocalls only say "press 1". The ask (money, card details, an app) comes later from the human the victim is connected to, and the recordings stop before that. Amber is the right warning at that point. For FTC, the detection number is red or amber, as the evaluation rule says.
- **The one miss:** a fragment of a fake power-company call that starts mid-sentence ("…would like to stop the disjoin, please press 1 to start your claim"). The transcriber heard "disconnection" as "disjoin", so only A10 is left. Not chased further: a keyword for a mis-hearing would be fitting the dev set, not the scam.
