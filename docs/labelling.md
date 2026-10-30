# The labelling sheet

Version 1, Oct 28, 2026. One CSV row per call, made **by listening, before the system's output on that call has been seen** ([evaluation-rule.md](evaluation-rule.md)). Template: [labels-template.csv](labels-template.csv). Check a sheet with:

```bash
teesrakaan labels data/labels.csv
```

Labels for donated real calls live in `private/` with the audio, never in the repo.

## Columns

| Column | What to write | Example |
|---|---|---|
| `call_id` | The call file's id | `IS07` |
| `set` | `IN-real`, `IN-scam`, `IN-genuine` or `FTC` | `IN-scam` |
| `split` | `dev` or `test`, from `teesrakaan split` (IN) or the FTC hash sample, never chosen by hand | `test` |
| `is_scam` | `1` scam, `0` genuine | `1` |
| `pattern` | 1–9 from [scam-tactics.md](scam-tactics.md); `0` for genuine or none | `1` |
| `languages` | ISO codes joined with `+`, main language first: `hi`, `mr`, `en` | `hi+en` |
| `t0` | When the caller makes the **first scam move**: the first false claim or pressure (A1–A4, A8–A10, A12). Seconds or `m:ss.s` | `0:04.5` |
| `t_ask` | When the caller **first asks** for secrets, money, an app or link, or a PIN to receive (A5, A6, A7, A11). Blank if they never ask | `1:01` |
| `ftc_class` | FTC only: `impersonation` (poses as a government body, bank or company and pushes an action), `sales` (warranty, insurance, solar, debt relief…) or `other` | `impersonation` |
| `labeller` | Initials | `AG` |
| `labelled_at` | When the label was made, ISO time with zone | `2026-10-29T18:05+05:30` |
| `notes` | Anything unusual: bad audio, two patterns, a cut-off call | `starts mid-call` |

The checker refuses a sheet when: an IN scam call has no `t0`; a genuine call has a `t0` or `t_ask`; `t_ask` comes before `t0`; an FTC row has no `ftc_class`; a split isn't `dev` or `test`; `labelled_at` is empty; or a `call_id` repeats.

## How to mark the times
The studio (`teesrakaan studio`, [recording.md](recording.md)) does steps 1, 4 and 5 for you and writes `data/labels-in.csv`; the rules are the same.

1. Play the call from the start, with the waveform visible (the studio, Audacity, or any player that shows seconds).
2. **`t0`:** stop at the first word of the first scam move. "Main CBI se bol raha hoon" → the time of "Main". Greetings and "am I speaking to…" don't count.
3. **`t_ask`:** the first word of the sentence that asks. "Verification ke liye paise transfer kariye" → the time of "Verification".
4. Round to the nearest half second. Write what you hear; if unsure, write the earlier time and a note.
5. Fill `labelled_at` when the row is done, before running anything on that call.

## Why these rules
- **Labels first, output second,** so a label can't be nudged toward what the system did.
- **Times from the audio,** not the transcript, so transcription delays count against the system, as they would on a real call.
- **`t_ask` is separate** because the most useful warning comes before the caller asks: "warned before the ask" is one of the headline numbers.
