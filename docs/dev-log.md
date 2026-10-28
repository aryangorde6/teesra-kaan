# Development log

Every change to the signals, rules, keyword lists or the Spark prompt, with the **dev** numbers before and after. Test sets are never used here. Dev numbers are optimistic by construction, because the changes were made by looking at these same calls; only the frozen test run counts.

## Oct 28, 2026, 19:30 IST: FTC dev, keyword baseline, rules v1.1 → v1.2
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

## Oct 28, 2026, 19:38 IST: re-enactment dev scripts, keyword baseline v1.2b
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

## Oct 28, 22:23 IST: the next line
- **Why:** detecting scam calls isn't new (Google, Hiya, Truecaller), and a plain warning can lose to fear: a Rajkot doctor sent ₹58.5 lakh in Oct 2026 after her bank warned her. Showing the caller's next line before they say it proves the call is a script.
- **What:** `playbook.py` turns the nine patterns into ordered scripts. A prediction needs two steps of a script heard, and every best-matching script must agree on the next step; after "police" + "FIR" alone it waits.
- **Demo calls only (not an evaluation):** in the written digital-arrest call, "come on a video call" is shown 24 s before the caller says it, and "transfer the money" 11 s before; in the Marathi TRAI call, "tell me the OTP" 13 s before. The genuine bank call shows one prediction ("transfer money") that never comes true. Metric 7 in `evaluation-rule.md` measures this on dev and test.
- **Prior work, to cite:** ScriptMind (arXiv 2601.13581, Korean phone scams, simulated calls) and PreScam (arXiv 2605.12243, a benchmark; LLMs predicted next steps only moderately). Neither is live, in Indian languages, or measured on real call audio.

## Oct 29, 2026, 01:37 IST: the next line on dev, keyword baseline v1.2b → v1.2c
- **Sets:** the 50 FTC dev calls (the dataset's transcripts) and the 28 dev scripts (text, estimated timings). **Judge:** keywords (comparison A). Playbook v1, rules v1.2. Metric 7 as coded in `metrics.py`.

| Keywords | IN-scam: next line came true | Naive guess | Median s ahead | Scam calls with one | IN-scam warned / red | IN-genuine amber or red | FTC: came true (naive) | FTC impersonation warned |
|---|---|---|---|---|---|---|---|---|
| v1.2b | 3/13 (8–50%) | 0/13 (0–23%) | 1 s | 9/16 | 16/16 / 14/16 | 0/12 | 0/9 (1/9) | 40/41 |
| v1.2c | 6/16 (18–61%) | 2/16 (3–36%) | 2 s | 9/16 | 16/16 / 14/16 | 0/12 | 0/9 (1/9) | 40/41 |

- **Why most v1.2b predictions missed:** 9 of 13 named a step the keyword stand-in never found, though the caller said it in other words. "200 grams of MDMA… linked to a drug trafficking case" (IS04), "पार्सल में ड्रग्स… मिले हैं" (IS13) and "140 gram MDMA mila hai" (IS24) weren't read as a legal threat (A2); "Do not inform your family" (IS33) wasn't read as secrecy (A4). Muse Spark judges meaning, so run C is the real measure, once the credits arrive.
- **What changed (comparison A's keyword lists only; signals, rules and playbook unchanged):**
  - A2: drugs "found", MDMA, narcotics, trafficking, and a case "linked" to you: the courier opening of pattern 2;
  - A4: "don't inform".
  - Nothing narrower: IS24's "don't keep any family member in the room" is one script's wording, so it's left out.
- **What it says about the feature:** in these short written scripts the lines come true only seconds ahead (median 2 s). The caller often says the next step in the very next breath, before the judge's answer is back, and a line said before it's shown doesn't count. The demo call's 24 s and 11 s came from a longer call with the listener talking in between. Don't promise a lead time on screen until the test run gives one.
- **FTC:** 0 of 9 came true, as the rule expected: robocalls stop at "press 1".
