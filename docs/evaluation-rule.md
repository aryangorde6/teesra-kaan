# Evaluation rule

Version 1.6.1, Nov 2, 2026 (12:25 IST), after the freeze and **before any person recorded a test call**; it changes nothing that decides a warning (v1.6 at 12:07 the same day). The freeze was taken on v1.5.2, Oct 31, 2026 (20:36 IST), **before any test call was recorded, run or opened** (v1 was written Oct 28, before any result existed; see "Changes" at the end). Any change is a new version with its date and reason, and the README reports which version produced each number.

## The question
When a scam call is on speaker, does Teesra Kaan warn **in time** (ideally before the caller asks for money or secrets), **without** crying wolf on genuine calls, in Hindi, Marathi and English?

## Test sets

| Set | What it is | Size (target) | Used for |
|---|---|---|---|
| **IN-real** | Real scam calls received by Indian families and donated with written consent (see the outreach consent note). Private, never published. | ≥10 | **Test only.** Never used for tuning. |
| **IN-scam** | Re-enacted scam calls in Hindi, Marathi, English and Hinglish, scripted from the documented patterns in `scam-tactics.md`. Voiced by people who agreed, and labelled as re-enactments everywhere. | ≥40 | Dev and test, split by script |
| **IN-genuine** | Re-enacted genuine calls that sound alarming but aren't scams: real bank fraud alerts, couriers, family asking for money, hospitals, telemarketing. | ≥30 | Dev and test, split by script |
| **FTC** | Real US robocalls from the FTC's Project Point of No Entry, via NCSU's Robocall Audio Dataset (public domain). English. | 200 sampled | Dev and test |
| **IN-synth** | **Synthetic voices, not people:** the IN test scripts in Hindi, Marathi and English, and the paraphrase scripts, spoken by an open text-to-speech model and passed through a phone band (see "The synthetic set"). | 33 test + 9 paraphrase | Test only. A fallback for Indian-language audio, never pooled with people's recordings |

**Splits:**
- **IN-scam and IN-genuine:** every script is written and numbered first. A shuffle with seed `20261028` then assigns 40% to dev and 60% to test, before anything is recorded.
- **FTC:** the 1,378 English rows of `metadata.csv` are 1,353 distinct recordings (25 are listed under two FTC cases). The distinct file names are sorted by `sha256(file_name)` and the first 200 are taken. The first 50 of those are dev, the other 150 test. The dataset is pinned to commit `5aa6f3b`, and every file is checked against its git hash (`teesrakaan ftc-fetch`).
- **Test audio** is not listened to or inspected by anyone working on prompts or rules until the freeze.

## The synthetic set (IN-synth, added in v1.5)
People's recordings stay the real test. This set exists so there are Indian-language results on audio even if fewer of them are recorded than planned, and it is always called synthetic.
- **What:** every test script in Hindi, Marathi or English (18 scam, 15 genuine) and every paraphrase script but one (9). The Hinglish scripts are left out: they're written in Latin letters, which the Hindi voices can't read.
- **How** ([`eval/synthetic.py`](../eval/synthetic.py)): the same pipeline as the synthetic pre-check on dev ([dev-log.md](dev-log.md), Oct 30, 16:14), unchanged since. Kokoro v1.0 (open weights, Apache 2.0), one voice for the caller and another for the listener: `hm_omega`/`hf_alpha` for Hindi and Marathi (`hm_psi`/`hf_beta` when both speakers are the same gender), `am_michael`/`af_heart` for English (`am_adam`/`af_bella`). Kokoro has no Marathi voice, so Marathi is read by a Hindi voice. 0.6 s between turns, 0.5 s before the first. Then 300–3,400 Hz through 8 kHz, with pink noise (amplitude 0.012, seed 7), 16 kHz mono.
- **Fixed before the freeze:** the audio is made before the freeze and the SHA-256 of every file is committed ([`eval/synth-audio.sha256`](../eval/synth-audio.sha256)), so it can't change afterwards. Nobody listens to it or transcribes it before the freeze.
- **Labels** ([`eval/synth-labels.csv`](../eval/synth-labels.csv)), from each script's text before any run: `t0` is the start of the caller's first line with a scam move (A1–A4, A8–A10, A12), `t_ask` the start of the caller's first line with an ask (A5, A6, A7, A11). The times come from the audio's own manifest, which is exact because the audio is built line by line. Sets `IN-synth-scam` and `IN-synth-genuine`; splits `test` and `paraphrase`.
- **Runs:** after the freeze, transcribed once with the same settings as everything else, then A, B and C once each. The paraphrase ones also get the keyword count.
- **Reported** in their own rows, always as synthetic voices, never pooled with people's recordings and never as a headline. They say nothing about real voices, accents, rooms or speakerphones.

## People's recordings after the freeze (added in v1.6)
No person had recorded a test call by the freeze. The system is frozen, so recording the test scripts now tests the frozen system on real voices, with nothing left to tune.
- **Who:** Aryan, with anyone who agrees in writing to play the other part ([recording.md](recording.md), Consent). The calls are re-enactments of the test scripts, said in their own words, on a real phone call on speaker, recorded by the laptop in the room ([recording.md](recording.md), Setup).
- **Solo takes (v1.6.1):** when nobody can play the other part, a test card may be recorded by one person, as the paraphrase cards may (Robustness, Solo takes). The reader says the caller's lines in their own words; the listener's lines are Kokoro's, made before any take, and the studio lays each into the take at the moment it showed that line, about 2 dB below the reader's loudness, then passes the whole take through the phone band. Nothing is played aloud. Every comparison judges the caller's words, so the part that is judged is a real voice in a real room; the listener's voice and the phone line are not. Each such label says "solo take", and the row says how many were solo ("caller: a person; listener: a synthetic voice; phone line simulated").
- **Which, in what order:** the 42 test scripts (24 scam, 18 genuine; the same scripts the synthetic set read, plus the 9 Hinglish ones it couldn't) in a fixed order, and the 10 paraphrase cards in another: [`eval/scripts/record-order.csv`](../eval/scripts/record-order.csv), made by [`eval/record_order.py`](../eval/record_order.py) with seed `20261102`, scam and genuine interleaved 24 to 18. Recorded in that order, without skipping.
- **When it stops:** recording and labelling end **Tue Nov 3, 14:00 IST**, or sooner when a list is done. The calls recorded and labelled by then are run once (`eval/after_freeze.sh`), whatever their number, and reported as "n of 42 in the fixed order". A list cut short is a prefix of the order, so the order, not a choice, decides which calls are in.
- **Retakes:** a take may be recorded again only for a recording fault (the call dropped, someone laughed, a noise drowned a line), and always before the run; nothing is run on any take before the cutoff.
- **Labels:** `t0` and `t_ask` marked by listening in the studio, before the run, as for every re-enactment.
- **Reported** as their own rows (IN test and paraphrase, people's re-enactments), labelled as re-enactments, with how many were solo, never pooled with the synthetic or FTC rows. The audio stays private unless every voice on it ticked publication.
- **What happened (Nov 3, 11:39 IST, at submission):** none of the 42 test cards or 10 paraphrase cards had been recorded, so there is nothing to run and no row to report. The Indian test numbers stay the synthetic ones.

## Labels (made before the system runs on a call)
- **Every call:** scam or genuine; pattern number from `scam-tactics.md`; language(s).
- **Every IN scam call:**
  - **t0**, the time of the caller's first scam move (the first false claim, pressure or lure: A1–A4, A8–A10, A12);
  - **t_ask**, the time of the first ask (A5, A6, A7 or A11), if there is one.

  Marked by listening, in the labelling sheet ([labelling.md](labelling.md)), before the system's output on that call has been seen.
- **FTC:** each call is labelled from its audio and the dataset transcript as one of the classes below. **Dev calls are labelled now; the 150 test calls are labelled after the freeze and before the test run,** so nobody working on prompts or rules reads them early:
  - **impersonation scam:** poses as a government body, bank or company and pushes an action;
  - **sales robocall:** warranty, insurance, solar, debt relief and similar;
  - **other.**

## Metrics
1. **Caught:** the share of scam calls with a red warning, and with red or amber. Both are reported with Wilson 95% intervals, per set and per language.
2. **False alarms:**
   - red warnings per genuine call (IN-genuine), the headline number;
   - amber warnings per genuine call, reported separately.
3. **Time to warning** (IN sets, streaming mode): the median and 90th percentile of `t_warn − t0`, in seconds, where `t_warn` is when the first warning (amber or red) is on screen. The same for the first red is reported beside it.
4. **Warned before the ask:** the share of scam calls with an ask where `t_warn < t_ask`.
5. **FTC:** red-or-amber rate on impersonation scams (the detection number) and on sales robocalls (reported, not counted as false alarms, since these calls are illegal anyway).
6. **Cost** per minute of audio, from the API usage figures.
7. **The next line** (`src/teesrakaan/playbook.py`, scripts v1): a prediction *comes true* when the caller says the predicted step at or after the moment it was shown (a step found later but said earlier doesn't count). Reported per set, with Wilson 95% intervals:
   - **came true:** the share of predictions that came true;
   - **against a naive guess:** the same share for a guess made at the same moments, naming the signal found on the most calls of the set (ties by signal number) among those not yet found, which comes true on the same terms. Its counts come from the calls it's scored on, which favours it, so it's reported on dev only;
   - **lead time:** the median seconds between a prediction being shown and the caller saying it;
   - **reach:** the share of scam calls with at least one prediction shown;
   - **on genuine calls:** predictions shown per genuine call (IN-genuine).
   FTC robocall recordings usually end at "press 1", before any ask, so their "came true" share is reported but expected to be low.

**Streaming mode:** audio is fed to the system at real-time speed, in the same chunks the live page sends. Every timing includes transcription and model latency.

## Bars
- **Gate G2, Sat Oct 31, 12:00 IST, on dev only:**
  - ≥80% of IN-scam dev calls caught (red or amber);
  - ≤1 red false alarm per 10 IN-genuine dev calls.

  **If either bar fails:** fix and re-check once that day. If they still fail, the README and video report the real numbers and the claim gets smaller. Bars are never redefined after results.
- **Freeze, Sun Nov 1, 12:00 IST:** everything that decides a warning is frozen with the git tag `eval-freeze`:
  - prompts, signal questions, rules and thresholds;
  - model names and versions;
  - language and keyword settings.

  **Then each test set is run once and reported as it comes out.** A fix after the freeze is reported as an extra "after freeze" row and never replaces the frozen row.

## Comparisons (on test, same run, after the freeze)
- **A. Keyword baseline:** the fixed keyword lists in `src/teesrakaan/keywords.py` answer the same signal questions, and rules v1.2 decide (two signals warn), since keywords can't give an overall view. No Muse Spark. So A vs C measures what Spark adds: its answers and its overall view.
- **B. Muse Spark free-form:** "Is this call a scam? yes/no" after each turn.
- **C. Teesra Kaan:** Spark's yes/no signal questions, each quoted and checked, plus fixed rules (v1.3), which also need B's answer to be "scam". So B vs C shows what the quoted signals cost or save against Spark's view alone.
- **Ablations of C:**
  - without speaker separation;
  - without the language hint;
  - without keyword biasing in transcription.

## Robustness
- **Speakerphone:** the IN test calls are played through a phone speaker and re-recorded on the laptop microphone in a normal room. Report how much "caught" and "time to warning" change.
- **Paraphrase:** 10 test scam scripts are rewritten to avoid every keyword in the baseline's list, recorded, and run once after the freeze.
  - **Which 10:** `random.Random(20261028).sample` of the 24 test scam IDs, sorted: IS02, IS08, IS12, IS25, IS27, IS31, IS32, IS36, IS37, IS38 (2 Marathi, 4 Hindi, 3 English, 1 Hinglish).
  - **The rewrite** ([`eval/scripts/in-paraphrase.json`](../eval/scripts/in-paraphrase.json), IDs IP02 to IP38): the same pattern, roles, moves in the same order and ask (or none); only the words change. No pattern of `keywords.py` matches anywhere in a script, caller or listener (`tests/test_paraphrase.py`). Unlike the other re-enactments, they're read as written, so the missing words stay missing.
  - **Recorded and labelled** like the others, into their own split, `paraphrase`; transcribed after the freeze; run once with A, B and C (`teesrakaan eval … --split paraphrase`) and reported as their own row.
  - **Keywords that come back anyway** (an actor's slip, or the transcription) are counted in each transcript and reported. The take stays in.
  - **Solo takes** (v1.5.1): a paraphrase card may be recorded by one person. They read the caller's lines as written; after each, the studio plays the listener's next line through the laptop's speaker, and the laptop's microphone records the room (since v1.6.1 the line is laid into the take instead, at the moment it was shown, and nothing plays aloud: People's recordings after the freeze, Solo takes). The listener's lines are spoken by Kokoro v1.0 with the synthetic set's main Hindi or English voice of the listener's gender, as the script's roles give it, made before any take ([`eval/solo_listener.py`](../eval/solo_listener.py); text, voice and SHA-256 of each in [`eval/solo-listener.json`](../eval/solo-listener.json)). The caller speaks in the room, not through a phone, so the saved take is passed through the synthetic set's phone band (300–3,400 Hz, through 8 kHz; no added noise); the untouched take is kept. Labelled by listening like the others, and the label's notes say "solo take". The paraphrase row says how many of its takes were solo ("caller: a person; listener: a synthetic voice"). Only paraphrase cards can be solo (since v1.6.1, test cards too); every other recording is two people.

## Reproducing
One command runs every set, comparison and ablation from the cached transcripts and writes `runs/eval-<date>/results.json` plus the README table. Real donated calls are excluded from the public run, since their audio is private. Their numbers are reported, with a note that the audio can't be shared.

## Honesty rules
- IN-real, IN re-enactments and FTC are always reported separately, never pooled into one headline.
- Re-enactments are labelled as re-enactments wherever they appear, including the video.
- The synthetic set is called synthetic wherever it appears, and its numbers never stand in for people's recordings.
- FTC calls are US English robocalls. They show the system works on real scam audio; they say nothing about Indian languages.
- **Small sets get their intervals shown.** For example, 9 of 10 caught is reported as "9/10 (60–98%)", not "90%".
- **Budget:** a hard stop in code at $100 of the $150 Meta credits, checked against Meta's own meter ([spending.md](spending.md)).

## Changes
- **v1.1, Oct 28, 2026 (evening), before any call was recorded, downloaded or run:**
  - the signals and rules moved to v1.1 (A12 Windfall added; see the "Changes" section of `scam-tactics.md`), so `t0` now counts A12;
  - `t_warn` defined as the first amber or red, with the first red reported beside it;
  - comparison A defined exactly: the keyword lists plus the same rules;
  - the labelling sheet's format fixed in `labelling.md`.
- **v1.2, Oct 28, 2026 (19:20 IST), after downloading the FTC sample and before any call was run or listened to:**
  - the FTC sample is drawn from the 1,353 distinct English recordings, since 25 of the 1,378 English rows repeat a recording under a second FTC case;
  - FTC test calls are labelled after the freeze, before the test run (labelling them now would mean reading test transcripts);
  - 8 of the 200 sampled recordings are 8 kHz, not 16 kHz; they're kept as they are and sent to transcription unchanged.
- **v1.3, Oct 28, 2026 (22:23 IST), before any prediction had been run on an evaluation call:** added metric 7, the next line. The scripts are the nine patterns of `scam-tactics.md`, in the order their "How the call goes" column gives. They were checked only on the three written demo calls in `examples/calls/`.
- **v1.3.1, Oct 29, 2026 (01:21 IST), before any evaluation call had been run:** the naive guess of metric 7 written out exactly as `metrics.py` computes it (it had said "the signal most often still unsaid"). Nothing else changed.
- **Oct 29, 2026, 01:40 IST:** the times of v1.3 and v1.3.1 corrected to their commit times (they had been written as 22:50 and 01:30). No rule changed.
- **v1.3.2, Oct 29, 2026 (14:19 IST), before any paid call had been made:** the budget stop lowered from $120 to $100, so $50 of the credits is never touched and the card is never charged. Paid calls also need a recent reading of Meta's own meter. Nothing about the calls, labels, metrics or comparisons changed.
- **v1.4, Oct 30, 2026 (09:24 IST, commit `cfca2cf`), before the freeze, on dev only:** comparison C now uses rules v1.3 (`scam-tactics.md`): a warning needs Muse Spark's overall view, asked with comparison B's own prompt in a parallel call, to say "scam", plus at least one signal quoted in the caller's words. Both prompts are unchanged; only the rule combining them is new. Comparison A keeps rules v1.2. Why: on dev, v1.2 warned on 3 of 12 genuine calls (1 red) and missed 3 of 41 FTC impersonation calls; v1.3 warned on 0 of 12 and caught 41 of 41 ([dev-log.md](dev-log.md), Oct 30). No test call had been run or opened. Nothing else changed.
- **Oct 30, 2026, 13:10 IST:** the version line at the top raised from 1.3.2 to 1.4, which it had missed. No rule changed.
- **v1.4.1, Oct 31, 2026 (11:23 IST), before any test call was recorded:** the paraphrase test written out (Robustness): how the 10 scripts were drawn, the rewritten scripts, their own `paraphrase` split, read as written, and keywords that come back anyway counted and reported. Writing them meant reading those 10 test scripts' text, written on Oct 28 by the same author as the rules; no test audio exists, and nothing that decides a warning changed. The rewrites aren't run before the freeze, not even as text.
- **v1.5.1, Oct 31, 2026 (13:59 IST), before any test or paraphrase call was recorded:** solo takes for the paraphrase cards (Robustness). Why: none of the 10 had been recorded, and recording them needed two people. Every comparison judges the caller's words, so one person reading those, with a synthetic voice for the listener's short replies, keeps the part that's judged a real voice. Nothing else changed.
- **v1.5.2, Oct 31, 2026 (20:36 IST), before the freeze; no test call had been recorded, run or opened, and no test script was read for it:** signals v1.4 (A13 Credit message) and playbook v2 (pattern 10, "sent too much by mistake"), for comparisons A to C alike; A has no A13 keyword list (`scam-tactics.md`, Changes). Why: on Oct 31 an elder Aryan phoned had lost ₹20,000 to this call, and the playbook couldn't name it or predict its ask. It came from that person's account, not from any dev or test call. Rules v1.3 unchanged; checked on dev before the freeze (dev-log).
- **v1.5, Oct 31, 2026 (12:01 IST), before any test call was recorded and before the synthetic audio was made:** the synthetic set (IN-synth) added: what it is, how it's made (the dev pre-check's pipeline, unchanged), fixed by hashes before the freeze, labelled from the scripts' text, run once after the freeze, and always reported apart as synthetic. Why: no person had recorded a call by Oct 31, a day before the freeze. Nothing that decides a warning changed.
- **v1.6, Nov 2, 2026 (12:07 IST), after the freeze; no person had recorded a test or paraphrase call:** people's recordings after the freeze (the section of that name): who records, the fixed recording order (seed `20261102`), the cutoff (Tue Nov 3, 14:00 IST), retakes for recording faults only, and their own rows. Why: the Indian test calls so far are synthetic voices, and no donated call came. Nothing that decides a warning changed; the system stays at the `eval-freeze` tag.
- **v1.6.1, Nov 2, 2026 (12:25 IST), after the freeze; still no person had recorded a test or paraphrase call:** solo takes for the test cards, and every solo take's listener laid into the take rather than played through the laptop's speaker (People's recordings after the freeze, Solo takes). Why: Aryan's sister has exams this week and can't record, and the laptop's speaker crackles, so playing the listener aloud would put that crackle into every take. The listener lines for the 42 test cards are made by `eval/solo_listener.py` like the paraphrase ones, which are unchanged (the Hinglish ones spelled in Devanagari for the Hindi voice, the same words). Who records is now Aryan with anyone who agrees in writing. Nothing that decides a warning changed.
