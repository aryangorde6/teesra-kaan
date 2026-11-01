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

