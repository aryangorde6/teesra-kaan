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

## Oct 28, 2026, 20:30 IST: re-enactment dev scripts, keyword baseline v1.2b
- **Set:** the 28 dev scripts (16 IN-scam, 12 IN-genuine) after the seeded split. **Not recordings:** the script text with estimated timings (`src/teesrakaan/scripts.py`). These are the words actors are given, so they flatter any keyword list; real speech will differ.
- **Judge:** keywords (comparison A). Rules v1.2.

| Keywords | IN-scam warned | IN-scam red | IN-genuine amber or red |
|---|---|---|---|
| v1.2 | 13/16 | 10/16 | 1/12 (red: "video call karungi" read as a channel switch) |
| v1.2b | 16/16 (81–100%) | 14/16 (64–97%) | 0/12 (0–24%) |

- **What changed in the keyword lists (comparison A only; the signal questions didn't change):**
  - Devanagari matching ignores the nukta dot, so "एफआईआर" also matches "एफ़आईआर";
  - A2: "pakad liya", "पकड़ा गया", "arrested";
  - A4: "mummy papa ko mat batana", "किसी को बताया तो";
  - A6: "chahiye", "जमा करनी / jama karna", amounts written as numbers, "फ़ीस";
  - A7: "share your screen";
  - A8: "video call" or "WhatsApp" now needs a move verb nearby ("pe aaiye", "join", "रहिए"), not a mention;
  - A12: "bonus".
- **The 2 scams still amber:** IS04 and IS21 never reach an ask (the courier opening only), so amber is the intended warning.
- **FTC dev unchanged:** impersonation warned 40/41.
