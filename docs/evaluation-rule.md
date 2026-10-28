# Evaluation rule

Version 1.1, Oct 28, 2026, **before any result exists** (v1 was written the same afternoon; see "Changes" at the end). Any change is a new version with its date and reason, and the README reports which version produced each number.

## The question
When a scam call is on speaker, does Teesra Kaan warn **in time** (ideally before the caller asks for money or secrets), **without** crying wolf on genuine calls, in Hindi, Marathi and English?

## Test sets

| Set | What it is | Size (target) | Used for |
|---|---|---|---|
| **IN-real** | Real scam calls received by Indian families and donated with written consent (see the outreach consent note). Private, never published. | ≥10 | **Test only.** Never used for tuning. |
| **IN-scam** | Re-enacted scam calls in Hindi, Marathi, English and Hinglish, scripted from the documented patterns in `scam-tactics.md`. Voiced by people who agreed, and labelled as re-enactments everywhere. | ≥40 | Dev and test, split by script |
| **IN-genuine** | Re-enacted genuine calls that sound alarming but aren't scams: real bank fraud alerts, couriers, family asking for money, hospitals, telemarketing. | ≥30 | Dev and test, split by script |
| **FTC** | Real US robocalls from the FTC's Project Point of No Entry, via NCSU's Robocall Audio Dataset (public domain). English. | 200 sampled | Dev and test |

**Splits:**
- **IN-scam and IN-genuine:** every script is written and numbered first. A shuffle with seed `20261028` then assigns 40% to dev and 60% to test, before anything is recorded.
- **FTC:** the 1,378 English calls are sorted by `sha256(file_name)` and the first 200 are taken. The first 50 of those are dev, the other 150 test.
- **Test audio** is not listened to or inspected by anyone working on prompts or rules until the freeze.

## Labels (made before the system runs on a call)
- **Every call:** scam or genuine; pattern number from `scam-tactics.md`; language(s).
- **Every IN scam call:**
  - **t0**, the time of the caller's first scam move (the first false claim, pressure or lure: A1–A4, A8–A10, A12);
  - **t_ask**, the time of the first ask (A5, A6, A7 or A11), if there is one.

  Marked by listening, in the labelling sheet ([labelling.md](labelling.md)), before the system's output on that call has been seen.
- **FTC:** each call is labelled from its audio and the dataset transcript as one of:
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
- **A. Keyword baseline:** the fixed keyword lists in `src/teesrakaan/keywords.py` answer the same signal questions, and the same rules decide. No Muse Spark. So A vs C measures what Spark adds, nothing else.
- **B. Muse Spark free-form:** "Is this call a scam? yes/no" after each turn.
- **C. Teesra Kaan:** Spark's yes/no signal questions plus fixed rules.
- **Ablations of C:**
  - without speaker separation;
  - without the language hint;
  - without keyword biasing in transcription.

## Robustness
- **Speakerphone:** the IN test calls are played through a phone speaker and re-recorded on the laptop microphone in a normal room. Report how much "caught" and "time to warning" change.
- **Paraphrase:** 10 test scam scripts are rewritten to avoid every keyword in the baseline's list, recorded, and run once after the freeze.

## Reproducing
One command runs every set, comparison and ablation from the cached transcripts and writes `runs/eval-<date>/results.json` plus the README table. Real donated calls are excluded from the public run, since their audio is private. Their numbers are reported, with a note that the audio can't be shared.

## Honesty rules
- IN-real, IN re-enactments and FTC are always reported separately, never pooled into one headline.
- Re-enactments are labelled as re-enactments wherever they appear, including the video.
- FTC calls are US English robocalls. They show the system works on real scam audio; they say nothing about Indian languages.
- **Small sets get their intervals shown.** For example, 9 of 10 caught is reported as "9/10 (60–98%)", not "90%".
- **Budget:** a hard stop in code at $120 of the $150 Meta credits.

## Changes
- **v1.1, Oct 28, 2026 (evening), before any call was recorded, downloaded or run:**
  - the signals and rules moved to v1.1 (A12 Windfall added; see the "Changes" section of `scam-tactics.md`), so `t0` now counts A12;
  - `t_warn` defined as the first amber or red, with the first red reported beside it;
  - comparison A defined exactly: the keyword lists plus the same rules;
  - the labelling sheet's format fixed in `labelling.md`.
