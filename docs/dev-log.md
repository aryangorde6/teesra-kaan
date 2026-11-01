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
- **Why:** detecting scam calls isn't new (Google, Hiya, Truecaller), and a plain warning can lose to fear: a Rajkot doctor sent ₹58.5 lakh in Sep 2026 after her bank warned her. Showing the caller's next line before they say it proves the call is a script.
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

## Oct 30, 2026, 01:14 IST: first Muse Spark calls (written demo calls and typed examples only, no evaluation call)
- **Key and spending:** one ping, then $0.14 in all through the ledger (58 calls). Meta's meter last read Oct 29 at $150.00 of credits and ₹0.
- **Reasoning eats the output limit.** With `reasoning_effort: low` and `max_tokens: 400`, Spark 1.3 spent about 398 tokens reasoning and returned an empty reply on 13 of 14 checks of the digital-arrest demo call. `none` is refused (the accepted values are minimal, low, medium, high, xhigh, max). With `minimal` it reasoned 144–361 tokens and still cut off 2 of 4 replies at 400. **Now `minimal` with `max_tokens: 1024`.** That gave 0 cut-off replies on all three demo calls (29 checks, longest reply 598 tokens), a median of about 2.1 s and a p90 of 2.7–3.3 s. Each check costs about $0.002.
- **Demo calls with Spark:**
  - digital arrest: red, with A1 A2 A9 A3 A4 A8 A6, every quote in the caller's words;
  - Marathi TRAI: red;
  - genuine bank alert: amber (A1, A2), not red.
- **Typed retellings ("check before you pay").** The call prompt answered no to every question on a first-person retelling of the Rajkot case: "A Mumbai Police officer called me… They said I will be arrested, and told me not to tell my family". It reads the text as the listener talking. The typed check now has its own prompt, `SPARK_SYSTEM_TYPED_V1`, which treats the account as a report of what the caller said. The evaluation's prompt is unchanged.
  - With it, the Rajkot reconstruction goes red (A1, A8, A2, A4), matches digital arrest, and shows **"Transfer the money for verification."** as the next step. The page's en/hi/mr examples give the same result.
  - This prompt was written after seeing the Rajkot text fail, and checked on it and the three examples only.

## Oct 30, 2026, 01:34 IST: run C (Muse Spark) on dev, rules v1.2, playbook v1
Dev only. These are the same inputs as the keyword runs: the 28 dev scripts (text, estimated timings) and the 50 FTC dev calls (the dataset's transcripts). $1.16 in all through the ledger, including one reverted trial.

| Set | Spark (C) | Keywords (A, v1.2c) |
|---|---|---|
| IN-scam warned / red | 16/16 / 14/16 | 16/16 / 14/16 |
| IN-genuine red (amber) | **1/12** (2 more amber) | 0/12 (0) |
| IN-scam: next line came true (naive) | 4/17 (3/17), 2 s ahead, 10/16 calls with one | 6/16 (2/16) |
| FTC impersonation warned / red | 38/41 / 0/41 | 40/41 |
| FTC: next line came true | 0/16 | 0/9 |

- **The red false alarm is IG03,** a daughter asking her mother for mess fees who adds "Sunday ko video call karungi". Spark answered A6 (money) and A8 (video call), both fair readings of the questions, and an ask plus any signal is red.
  - **Trial, reverted:** A8 narrowed to "move *this* conversation". IG03 stayed red, and A8 was then missed in three scam scripts (IS09, IS28, IS35). Kept as `runs/dev/*A8-trial-reverted*`; the signals stay v1.2.
  - **The honest limit:** a relative asking for money plus one more signal goes red. It's hard to tell from the "Hi Maa, new number" scam without the caller's history.
- **The next line with Spark:** Spark finds signals sooner than keywords, often several in one turn (IS16: A3 and A6 at 16 s), so there's less gap to predict into. Some keyword "hits" came from keywords catching a step late (IS13: A2 at 16 s by keywords, at 0 s by Spark).
  - These are short text scripts. The re-enactment recordings are the real measure. The playbook isn't changed on this.

## Oct 30, 2026, 09:06 IST: first Muse Voice Transcribe session, and who said what
One FTC dev robocall (`ftc-0081c9355a`, 34 s) streamed through `teesrakaan transcribe` at real time: 56 events, no close-code errors, so the pacing is right.
- **Words arrive about 0.3 s behind the audio** (each partial's `received` against its `audioProcessedMs`).
- **The `speaker` label comes at the end of each turn,** together with `speechEnd`, after all of that turn's words. The runbook asked to check exactly this.
- **That was a bug in live listening.** `live.py` gave stable words to the Listener as partials came in, under the default label "A", before the label existed. On a speakerphone call, the person being called could have their own words ("should I transfer the money?") read and quoted as the caller's. The evaluation hid it, because `session_to_call` applied each turn's label in hindsight.
- **Fixed, the same way in both places:**
  - Live listening now waits for a word's label before the Listener sees it. Until then the page shows the words as grey partial text.
  - The evaluation counts a word as heard only when its label arrived, so the reported times include this wait.
  - A label in the middle of a turn splits it.
  - Two new tests cover this. The live one fails on the old code.
- **The cost:** the judge sees a turn when it ends, not every 6 s within it. For long robocall monologues that delays a warning by up to one turn. Conversations have shorter turns. The FTC dev transcripts measure it.

## Oct 30, 2026, 09:11–09:22 IST: real audio, comparison B, and rules v1.3
Dev only.
- **Transcription of the 50 FTC dev calls** (`transcribe-set` on a folder holding only the dev audio, linked by call id): all 50 transcribed, none failed. 19.5 min of speech for about $0.06.
- **Comparison B on dev** (Spark asked "is this a scam?", no signals, no rules):

| Set | B | C, rules v1.2 | A, keywords |
|---|---|---|---|
| IN-scam scripts warned / red | 16/16 / 16/16 | 16/16 / 14/16 | 16/16 / 14/16 |
| IN-genuine scripts amber or red | **0/12** | 3/12 (1 red) | 0/12 |
| FTC impersonation warned (real transcripts) | **41/41** | 38/41 | 40/41 |
| FTC sales warned | 8/8 | 2/8 | 6/8 |

- **What it says:** asked plainly, Spark is a very good detector. On the FTC transcripts B warned about 1 s before C on most calls; C's reply is longer, so it takes longer. B has no quote and no next line, so it can't show why. C's three FTC misses were short robocalls with only one signal each ("we just suspend your social security number… press 1"); C's genuine-call alarms came from family and bank calls with two signals.
- **Estimated from the saved runs:** requiring B's "scam" plus at least one of C's quoted signals would keep every scam call and none of the genuine ones.
- **Rules v1.3, so built (Oct 30, ~09:15).** `CheckedJudge` asks Spark both prompts in parallel, each unchanged: the signal questions (prompt v1) and B's question. A warning needs B's "scam" and at least one quoted signal. Red means an ask, or the digital-arrest opening. The overall view is kept apart from the signals: it isn't shown as a sign, has no quote, and isn't counted by metric 7's naive guess. The keyword baseline keeps v1.2, since it has no overall view. Evaluation rule v1.4.
- **Rules v1.3 on dev** (every Spark reply came from the cache, $0):

| Set | C, rules v1.3 | C, rules v1.2 |
|---|---|---|
| IN-scam warned / red | 16/16 / 14/16 | 16/16 / 14/16 |
| IN-genuine amber or red | **0/12** | 3/12 (1 red) |
| FTC impersonation warned | **41/41** | 38/41 |
| FTC sales warned | 8/8 | 2/8 |
| Next line, IN-scam | 4/17, as before | 4/17 |

  - Time to warning: the same median, 4 calls earlier and 2 later (the latest by 11 s, when B said scam after two signals had already been quoted).
  - Cost: $0.0179 per minute of audio, against $0.0155 for v1.2 (FTC dev, list prices).
  - **Demo calls:** the genuine bank alert is now silent (it was amber). The digital arrest is still amber at 18.5 s and red at 45.0 s, the same as v1.2. The Marathi TRAI call is still red.
  - **Typed check:** the Rajkot retelling and the en/hi/mr examples are still red, with "Transfer the money for verification." next. The typed check has its own B prompt (`FREEFORM_SYSTEM_TYPED_V1`), as it already had for the signals.
  - **Caveat:** 12 genuine dev calls is a small set (0/12 is 0–24%). The 42 recorded test calls decide.
- **Live listening end to end:** one FTC dev call streamed at real time through the page's `/ws/live` with the real APIs (the test client, not a browser). Words arrived about 0.3 s behind the audio. The quote was checked, and the call ended with its report.

## Oct 30, 2026, 16:14–16:21 IST: a synthetic-speech pre-check of Hindi and Marathi transcription
Dev only. **Synthetic speech, not the kill check and not a result:** no person has recorded a call yet, so this only asks whether Muse Voice Transcribe handles Hindi and Marathi at all before the recordings arrive.
- **How:** the 21 dev scripts written in Devanagari or English (7 Hindi, 8 Marathi, 6 English; the 6 Hinglish ones are in Latin letters and were left out) were spoken by Kokoro v1.0 (open weights, Apache 2.0), with one voice for the caller and another for the listener and 0.6 s between turns. Kokoro has Hindi voices but no Marathi one, so Marathi is a Hindi voice reading Marathi. Each call was then passed through a phone band (300–3,400 Hz, through 8 kHz) with light pink noise. That gave 9.0 min of audio, transcribed with the same settings as everything else (`transcribe-set`, language bias HI/MR/EN). The audio and transcripts stay in `data/` and the results in `runs/dev/` (both gitignored).
- **Transcription against the script** (character error rate, punctuation ignored):

| | Hindi (7) | Marathi (8) | English (6) |
|---|---|---|---|
| Phone band and noise | 5.4% | 18.6% | 1.2% |
| The same audio, clean | 3.8% | 8.6% | 1.2% |
| Words given to the right voice (phone band) | 93% | 93% | 95% |

  - Hindi and Marathi come back in Devanagari. English loanwords come back in Latin letters ("AnyDesk", "Metro Pathology Lab", "Constable"), which counts as an error here but keeps the meaning, so the rates overstate the damage.
  - **One real failure:** IG21, a 16-second Marathi call, came back partly in **Gujarati script** through the phone band, and correctly when clean. The language bias doesn't stop that on a short, noisy Marathi call.
  - Marathi "बँक" (bank) was misheard in both versions ("पिंकीच्या", "बेंकीच्या", once "बनावटच्या", meaning "of a fake…"). That may be the Hindi voice saying the Marathi sound; a person's voice will tell.
  - Speaker labels: the two voices were told apart, and "the caller is whoever has said the most" picked the right one on every call.
- **The runs on the phone-band transcripts, against the same scripts as text** (rules v1.3; every call compared one by one):
  - **Keywords (A):** the same level on 21/21 calls.
  - **Teesra Kaan (C, Muse Spark):** the same level on 20/21. Scam calls warned 12/12 (red 10/12), the same as text. Genuine calls red 0/9. **One genuine call went amber:** IG14, a Marathi bank fraud-desk call ("did you make this ₹15,000 payment?"), silent as text. Its transcript had "बँकेच्या" misheard twice, once as "बनावटच्या" ("of a fake…"), and Spark's overall view then said scam. On the clean transcript of the same call ("बेंकीच्या", but no "बनावट"), Spark quoted the same two signs, its overall view said no scam, and the call stayed silent. So the one word "fake" decided it.
  - The next line came true 4/11 (text: 3/12 on the same calls).
  - Cost: $0.22 for both transcriptions and the runs (ledger $1.64 → $1.86).
- **What it says:** speech-to-text in Hindi is close to the text. Marathi is the weak spot, and the phone channel roughly doubles its errors. Nothing was tuned on this. The kill check still needs people: two or three recorded calls (one Hindi, one Marathi) on a real speakerphone, which decide whether Marathi is usable.

## Oct 31, 2026, 11:25 IST: gate G2 (due 12:00 today), on what exists
- **Nothing that decides a warning has changed since rules v1.3** (`cfca2cf`, Oct 30, 09:24). The one later change to `spark.py` adds the replay client for the hosted page (`2f973f2`). The paraphrase cards added this morning (evaluation rule v1.4.1, `20a5fd8`) change nothing here either, and they aren't run before the freeze.
- **Re-run from Muse Spark's saved replies only** (no API call, $0; the ledger stayed at $1.8739): the 28 dev scripts as text give the same level, warning time and predictions on every call as Oct 30's run. IN-scam warned 16/16 (81–100%), red 14/16 (64–97%); IN-genuine red 0/12 (0–24%), amber 0/12; next line came true 4/17 (naive guess 3/17).
- **The bars:** at least 80% of scam calls warned: 16/16, passes. At most 1 red per 10 genuine calls: 0/12, passes. On synthetic speech (Oct 30, 16:21): 12/12 warned, red 0/9, amber 1/9.
- **What G2 can't say yet:** the bars are meant for recorded dev calls, and none has been recorded. So G2 passes on the scripts as text and on synthetic speech, not on people's voices. It's checked again the day the dev recordings arrive, and the README will say which it was.

## Oct 31, 2026, 12:54–13:03 IST: the kill check on real voices, and a script fix
Dev only, nothing from the test sets. **Real people, but not calls:** no one has recorded a call yet, so the kill check's question (does a speech model transcribe Hindi and Marathi usably?) was put to native speakers reading sentences aloud, from Google's FLEURS dataset (CC BY 4.0).
- **How:** the first 20 Hindi and first 18 Marathi clips in FLEURS's dev archives, in archive order, fixed before any was transcribed (the 18th Marathi clip was cut off by the 25 MB download cap, so 17). 7.4 min in all. Each clip was transcribed clean and through the same phone band and noise as the synthetic pre-check, with the same settings as everything else. Scored against FLEURS's own text: character error rate, pooled over the clips, punctuation ignored. The synthetic pre-check's transcripts were re-scored the same way so the columns compare (this measure gives slightly lower synthetic figures than the Oct 30 entry's).

| | Hindi, real (20) | Marathi, real (17) | Hindi, synthetic (7) | Marathi, synthetic (8) |
|---|---|---|---|---|
| Phone band, as transcribed | 11.1% | 25.0% | 4.6% | 12.1% |
| Phone band, Gujarati letters as Devanagari | 11.1% | 13.8% | 4.6% | 10.5% |
| Clean, as transcribed | 5.4% | 30.8% | 3.4% | 6.8% |
| Clean, Gujarati letters as Devanagari | 5.4% | 13.6% | 3.4% | 6.8% |

- **The Gujarati drift is the transcriber's, not Kokoro's:** 8 of the 17 real Marathi clips came back partly in Gujarati letters (4 through the phone band), often switching mid-sentence ("एका સંસ્થા નવીન્યપૂર્ણ … केले पाहिजे"). The words are mostly right, in the wrong letters. Hindi never drifted.
- **The fix, before the freeze:** Gujarati and Devanagari letters share one layout, so `asr.devanagari` writes any Gujarati letter as the same Devanagari one, wherever a transcript comes in (replay, batch uploads, live listening). No call in our sets is in Gujarati. It's part of transcription, so runs A, B and C all get it. Of the saved dev transcripts it touches one call, IG21 (synthetic, genuine, Marathi), which stays silent under A and C. FTC dev is English and unchanged.
- **What's left in Marathi** (phone band, after the fix; median clip 10.8%, 9 of 17 under 15%): numbers said as words ("दोन" for "2"), names in Latin letters ("Kruger National Park"), a few words romanized ("Vidnyanata darshu vidhe…"), and real mishearings, some toward Gujarati ("त्रण हजार", three thousand, for 7,000).
- **Verdict:** Hindi passes. Marathi passes with the script fix: usable, not clean. The project goes on, with no switch to the fallback. **What this can't show:** read sentences aren't a conversation, the phone band is simulated, and each clip has one voice. People's recorded calls still decide the test results.
- Cost: $0.05 (ledger $1.8739 → $1.9251). The clips and transcripts stay out of the repo (`data/` is gitignored).

## Oct 31, 2026, 14:48–14:56 IST: the paraphrase test's idea, tried on dev before the freeze
Dev only, nothing from the test sets. The paraphrase test (evaluation rule v1.4.1) is the row where keywords and Teesra Kaan should part ways, and it runs once, after the freeze. So the same rewrite was tried on the 16 dev scam scripts first, while a fix was still allowed.
- **What:** each dev scam script rewritten the way the test ones were: the same pattern, moves in the same order, ask (or none) and roles, and no pattern of `keywords.py` anywhere, caller or listener (`tests/test_paraphrase.py`). [`eval/scripts/in-paraphrase-dev.json`](../eval/scripts/in-paraphrase-dev.json), IDs DP04 to DP35, written by the same author as the rules; the wording isn't checked by a native speaker. Run as text with estimated timings, like the dev scripts in G2 ([`eval/dev_paraphrase.py`](../eval/dev_paraphrase.py)).

| Run | Warned (red or amber) | Red | Next line came true |
|---|---|---|---|
| A. Keywords | 0/16 (0–19%) | 0/16 (0–19%) | – (none shown) |
| B. Spark alone | 16/16 (81–100%) | 16/16 (81–100%) | – (B shows none) |
| C. Teesra Kaan | 16/16 (81–100%) | 14/16 (64–97%) | 7/16 (23–67%), shown on 11 of 16 calls |

- **The two ambers** (DP04, DP21) are the two scripts with no ask, as with their keywords (red needs an ask). With the keywords in, the same scripts gave C 16/16 warned and 14/16 red (G2).
- **B and C:** C's warning needs B's view too (rules v1.3), so it is never earlier: the same time on 14 of 16, later on DP21 (12 s against 6 s) and DP29 (22 s against 19 s). What C adds is in the warning itself: the quoted signs and the next line.
- **What it says:** with the keywords gone, the keyword baseline hears nothing, and Spark, alone or with the quoted signals, still hears every scam. If the test rewrites behave like these, the paraphrase row is where the difference shows. Nothing was changed: no fix was needed.
- **Cost:** $0.26 (ledger $1.9251 → $2.1885); B came from the cache of C's run.

## Oct 31, 2026, 15:03–15:12 IST: the same rewrites through synthetic speech
Dev only. The entry above ran the rewrites as text; this puts them through speech and transcription, the path the synthetic paraphrase row takes after the freeze. **Synthetic voices, not people.**
- **How:** [`eval/synthetic_dev_paraphrase.py`](../eval/synthetic_dev_paraphrase.py) runs `eval/synthetic.py`'s pipeline unchanged (the same Kokoro voices, phone band and noise) on the 12 rewrites that aren't Hinglish (6.7 min); the fixed synthetic set's hashes were checked before and after (unchanged). Transcribed with the same settings as everything else (`transcribe-set`, $0.02). `teesrakaan keywords`: no keyword came back in any of the 12 transcripts. Then A, B and C from the transcripts, with the transcription's real timing (`eval/dev_paraphrase.py <run> <out> data/transcripts/synth-dev-paraphrase`).

| Run | Warned (red or amber) | Red | Next line came true |
|---|---|---|---|
| A. Keywords | 0/12 (0–24%) | 0/12 (0–24%) | – (none shown) |
| B. Spark alone | 12/12 (76–100%) | 12/12 (76–100%) | – (B shows none) |
| C. Teesra Kaan | 12/12 (76–100%) | 10/12 (55–95%) | 3/10 (11–60%), shown on 7 of 12 calls |

- **The two ambers** are DP04 and DP21 again, the scripts with no ask.
- **B and C:** C's warning comes a median 1.2 s after B's (it waits for B's view and the quoted signs), 9.9 s on DP05.
- **The next line, 3 of 10 (7 of 16 as text):** of the 7 misses, 5 are calls that end before the predicted step (these scripts are 3 to 6 lines; the listener hangs up or the script stops), 1 went another way (DP33: screen sharing where the playbook expects the money ask), and 1 was said before it could be shown (DP04: the caller claimed to be an official at 13.0 s, the step was predicted at 14.5 s, because a step is known only once the transcript and Spark catch up). Nothing changed: fitting the playbook to 12 scripts by the same author would be fitting it to the check.
- **What it says:** through speech the picture holds: without keywords the baseline hears nothing, and Spark, alone or with the quoted signals, hears all 12. **Cost:** $0.14 (ledger $2.1885 → $2.3255).

## Oct 31, 2026, 20:17–20:19 IST: the scam that cost an elder ₹20,000, as a written probe
- **Why:** Aryan phoned 10 people today (5 elderly, 3 middle-aged, 2 Gen Z; README, "What people said"). Every one gets at least one scam call a week. One elder lost ₹20,000: the caller used the name of someone he knew, said he was sending ₹25,000, a fake SMS showed ₹45,000 credited, and the caller asked for the "extra" ₹20,000 back. It was never reported.
- **How:** that call written fresh from Aryan's description, in Hinglish and in English, with made-up names: [`eval/probe_wrong_credit.py`](../eval/probe_wrong_credit.py), as text with estimated timings. **Not a dev or test call, and never in a reported row.** Nothing was changed for it.

| Run | Hinglish | English |
|---|---|---|
| A. Keywords | red at the ask (38.3 s; "galti se" + the ask) | silent |
| C. Teesra Kaan | amber 29.0 s, at "sent too much by mistake" (A12), before any ask; red 38.3 s, at "send the rest back" (A6) | amber 25.7 s (A12); red 35.2 s (A6) |

- **The gap:** no script fits. A12 then A6 is also the prize script's order, so five scripts tie, the page names no scam and the next line shows nothing. Not changed before the freeze: the warning already comes, and a tenth script with the prize script's steps couldn't tell the two apart without a new question for Spark.
- **Cost:** $0.0425 (ledger $2.3255 → $2.3680); the re-run came from the cache.

## Oct 31, 2026, 20:30–20:50 IST: the tenth script, before the freeze (signals v1.4, playbook v2)
- **Why:** the probe above was warned on but matched five scripts, so the page named no scam and showed no next line, on a call that had cost a real person ₹20,000. Taught before the freeze (12:00 tomorrow), so the frozen test runs the system the page shows. From that person's account, not from any dev or test call; no test call was run or opened and no test script was read.
- **What changed** ([scam-tactics.md](scam-tactics.md) v1.4, [evaluation-rule.md](evaluation-rule.md) v1.5.2):
  - **A13 Credit message** (a flag): "says they are sending, or have sent, money to the listener, and points to an SMS or message as proof".
  - **Pattern 10, "sent too much by mistake"** (`wrong-credit`, A13 → A12 → A6), sourced from Kerala Police and Tripura Police warnings; its own lines for A12 and A6 ("Please send the extra back to this number"), and a fact: a "money credited" SMS is easy to fake, check the bank app.
  - **A6** also says "send back", and money the caller says he is sending you is not an ask: Spark had read "aapko pachees hazaar bhejne hain" as asking for money. **A12** loses "and must be returned", which the code had and the tactics table never did; with it, A12 waited for the ask.
  - Rules v1.3 unchanged. The keyword baseline gets no A13 list (`keywords.py` says why).
- **Dev, the 28 dev scripts as text** ([`eval/dev_scripts.py`](../eval/dev_scripts.py), `runs/dev/in-dev-scripts-C-v1.4.json`), against v1.3 (`in-dev-scripts-C-v1.3.json`):

| Run C | Warned (red or amber) | Red | Genuine: red / amber | Next line came true (naive guess) |
|---|---|---|---|---|
| v1.3, Oct 30 | 16/16 | 14/16 | 0/12 / 0/12 | 4/17 (3/17) |
| v1.4, tonight | 16/16 (81–100%) | 14/16 (64–97%) | 0/12 / 0/12 | 6/18 (4/18), median 2 s ahead |

  A13 was found on one dev scam (IS05) and no genuine call. No call's level changed.
- **The probe:** in Hinglish and in English, amber at "too much went by mistake", the next line "send the extra back" shown, came true at the ask, red. A demo call of it is on the page (`examples/calls/demo-wrong-credit.json`): amber at 28.0 s with the next line, the ask at 32.0 s, red and ticked at 40.5 s.
- **Not re-run with the new prompt:** FTC dev, the dev paraphrases and the synthetic dev calls, to keep tonight's spend small before the freeze run; the freeze run covers FTC and the paraphrase and synthetic test sets.
- **Cost:** $1.04 in all tonight (ledger $2.3255 → $3.3665), with the demo replies re-saved ($0.09).

## Nov 1, 2026, 12:00–12:30 IST: the frozen test run
- **The freeze:** `git tag eval-freeze` at 12:01, on `332732b` (Oct 31, 20:52, signals v1.4, playbook v2, rules v1.3). Nothing that decides a warning has changed since.
- **FTC test labels** committed before any test run (`957e873`, 12:02), drafted from the dataset's transcripts by [labelling.md](labelling.md) and the dev sheet's precedents: 132 impersonation, 16 sales, 2 other (borderline calls noted in the sheet).
- **Ran** (`eval/after_freeze.sh`, 12:02–12:29, log `runs/after-freeze-1202.log`): FTC test (150 calls; A, B, C, C-no-speakers) and the synthetic set (33 test and 9 paraphrase recordings; A, B, C), each once. **Skipped:** IN test (people's recordings) and the people's paraphrase takes: `data/recordings/` and `data/labels-in.csv` don't exist yet, so no ablation rows either.
- **FTC and IN test** (FTC only; `runs/eval-test/table.md`):

**FTC** (test)

| Run | Warned (red or amber) | Red | Red false alarms | Amber false alarms | Time to warning, median (90th pct) | Time to red, median | Warned before the ask |
|---|---|---|---|---|---|---|---|
| A | 121/132 (86–95%) | 11/132 (5–14%) | – | – | – | – | – |
| B | 132/132 (97–100%) | 132/132 (97–100%) | – | – | – | – | – |
| C | 131/132 (96–100%) | 0/132 (0–3%) | – | – | – | – | – |
| C-no-speakers | 131/132 (96–100%) | 0/132 (0–3%) | – | – | – | – | – |

The next line, **FTC**

| Run | Came true | Naive guess (dev only) | Median seconds ahead | Scam calls with one | Per genuine call |
|---|---|---|---|---|---|
| A | 0/13 (0–23%) | – | – | 13/132 (6–16%) | – |
| B | – | – | – | 0/132 (0–3%) | – |
| C | 0/43 (0–8%) | – | – | 41/132 (24–39%) | – |
| C-no-speakers | 0/43 (0–8%) | – | – | 41/132 (24–39%) | – |

  By FTC class (the sales and other calls are reported by class, never as false alarms): A warned 7/16 sales (red 0/16), 0/2 other; B 16/16 sales (red 16/16), 0/2 other; C and C-no-speakers 13/16 sales (red 0/16), 0/2 other.
- **Paraphrase:** no people's takes yet, so no table.
- **IN-synth, synthetic voices, not people** (`runs/eval-synth/table-test.md`):

**IN-synth-genuine** (test)

| Run | Warned (red or amber) | Red | Red false alarms | Amber false alarms | Time to warning, median (90th pct) | Time to red, median | Warned before the ask |
|---|---|---|---|---|---|---|---|
| A | 0/0 | 0/0 | 1/15 (1–30%) | 1/15 (1–30%) | – | – | – |
| B | 0/0 | 0/0 | 0/15 (0–20%) | 0/15 (0–20%) | – | – | – |
| C | 0/0 | 0/0 | 0/15 (0–20%) | 0/15 (0–20%) | – | – | – |

The next line, **IN-synth-genuine**

| Run | Came true | Naive guess (dev only) | Median seconds ahead | Scam calls with one | Per genuine call |
|---|---|---|---|---|---|
| A | – | – | – | – | 0.00 (0 on 15 calls) |
| B | – | – | – | – | 0.00 (0 on 15 calls) |
| C | 0/1 (0–79%) | – | – | – | 0.07 (1 on 15 calls) |

**IN-synth-scam** (test)

| Run | Warned (red or amber) | Red | Red false alarms | Amber false alarms | Time to warning, median (90th pct) | Time to red, median | Warned before the ask |
|---|---|---|---|---|---|---|---|
| A | 17/18 (74–99%) | 13/18 (49–88%) | – | – | 21 s (28 s) | 30 s | 8/16 (28–72%) |
| B | 18/18 (82–100%) | 18/18 (82–100%) | – | – | 21 s (27 s) | 21 s | 7/16 (23–67%) |
| C | 18/18 (82–100%) | 17/18 (74–99%) | – | – | 22 s (29 s) | 30 s | 7/16 (23–67%) |

The next line, **IN-synth-scam**

| Run | Came true | Naive guess (dev only) | Median seconds ahead | Scam calls with one | Per genuine call |
|---|---|---|---|---|---|
| A | 4/10 (17–69%) | – | 4 s | 7/18 (20–61%) | – |
| B | – | – | – | 0/18 (0–18%) | – |
| C | 5/8 (31–86%) | – | 5 s | 8/18 (25–66%) | – |


- **IN-synth paraphrase, synthetic voices, not people** (`runs/eval-synth/table-paraphrase.md`):

**IN-synth-scam** (paraphrase)

| Run | Warned (red or amber) | Red | Red false alarms | Amber false alarms | Time to warning, median (90th pct) | Time to red, median | Warned before the ask |
|---|---|---|---|---|---|---|---|
| A | 0/9 (0–30%) | 0/9 (0–30%) | – | – | – | – | 0/7 (0–35%) |
| B | 9/9 (70–100%) | 9/9 (70–100%) | – | – | 23 s (29 s) | 23 s | 4/7 (25–84%) |
| C | 9/9 (70–100%) | 8/9 (57–98%) | – | – | 25 s (30 s) | 29 s | 3/7 (16–75%) |

The next line, **IN-synth-scam**

| Run | Came true | Naive guess (dev only) | Median seconds ahead | Scam calls with one | Per genuine call |
|---|---|---|---|---|---|
| A | – | – | – | 0/9 (0–30%) | – |
| B | – | – | – | 0/9 (0–30%) | – |
| C | 3/7 (16–75%) | – | 12 s | 6/9 (35–88%) | – |


- **Keywords that came back in the synthetic paraphrase transcripts:** none; 0 in the caller's words and 0 in all on each of the 9 (IP02, IP08, IP12, IP25, IP27, IP31, IP32, IP36, IP38).
- **What the numbers show:** on FTC, C warned on 131 of 132 impersonation calls but never went red (these robocalls say "press 1" and never ask for money, a code or an app, which red waits for unless authority, threat and isolation come together), while B went red on every FTC call, sales included; on the synthetic paraphrases the keyword baseline heard nothing and B and C warned on all 9.
- **Cost:** $1.3794 (ledger $3.4185 → $4.7979, `teesrakaan budget` before and after); Billing last read 09:38, $146.65 left, ₹0.00.

## Nov 1, 2026, 12:25–12:37 IST: a security pass on the public page

Aryan asked which items on a common web-security checklist apply here. The page has no accounts, so CSRF tokens, object-level authorization, JWT, password hashing, MFA, tokens in localStorage, RLS and webhook signatures don't. These were already fine: the API key is only in `.env` (in no tracked file or commit); the ledger's SQL uses placeholders; nothing logs typed text or audio; `/voice/` checks its path; there's no CORS and no source maps; SSH is open to one address, IMDSv2 is required, and the service runs as a locked-down user. The public server has no key, so its paid features are off. Six things were worth fixing, none of which touches what decides a warning:

- **Limits:** per address, 30 demo calls, 20 typed checks, 5 recording checks and 6 live sessions a minute (`RateLimit` in `web/app.py`). Bodies are read only up to each endpoint's limit (32 KB typed, 25 MB recording), not whole first; Caddy refuses anything over 26 MB.
- **Headers:** a Content-Security-Policy (the page's own scripts and sockets, Google Fonts, the microphone's blob worklet), `nosniff`, no framing, `Permissions-Policy: microphone=(self)`, a referrer policy; HSTS from Caddy; no `server: uvicorn`.
- **Sockets:** `/ws/demo` and `/ws/live` refuse a browser page from another site (Origin must match Host).
- **Uploads:** `/api/check` passes only recognisable audio (WAV, MP3/AAC, Ogg, FLAC, WebM, AMR, CAF, MP4/M4A/3GP) to ffmpeg, so a playlist or concat file can't make ffmpeg open other files or URLs.
- **No `/openapi.json`.**
- **Pinned versions:** `deploy/push.sh` installs with `deploy/constraints.txt`, the 17 versions the tests passed with; none had a known vulnerability on OSV today.

Checked in the browser on the laptop: the demo calls, typed checks, fonts and the microphone worklet all work under the new policy, with no violations. It also showed that the timeline's "Warning" mark had no colour since the palette change (`--amber` became `--sun`); fixed. 215 tests pass.

**Deployed 12:39** (`deploy/push.sh teesrakaan`), once Aryan let the laptop's new address through the SSH rule; the new Caddyfile passed `caddy validate` on the server first. The pins moved four packages back to the tested versions (FastAPI 0.162.0 → 0.141.1, pydantic 2.14.2 → 2.14.0, pydantic-core 2.50.2 → 2.50.0, websockets 17.4 → 17.1; neither set has a known vulnerability on OSV). Checked on https://teesrakaan.aryangorde.com: every header above is sent; `/openapi.json` 404; a 27 MB post is refused by Caddy (413) and a 40 KB typed check by the app (413); the 21st typed check in a minute gets 429, and the server's log shows the visitor's own address, so the limit is per visitor, not shared through Caddy's 127.0.0.1; a socket opened with another site's Origin gets 403 and the site's own plays; in the browser, the digital-arrest demo plays to the end (Warning mark amber), the fonts and the microphone's worklet load, and nothing is blocked.
