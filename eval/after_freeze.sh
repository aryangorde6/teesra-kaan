#!/usr/bin/env bash
# After the freeze: every test set transcribed once, every comparison run once, then one table per group
# (docs/runbook.md, "After the tag, in this order", steps 3 to 5; docs/evaluation-rule.md, "Reproducing").
#
#     eval/after_freeze.sh
#
# Refuses before the eval-freeze tag, before the FTC test labels are committed, and while paid calls aren't
# allowed (`teesrakaan budget` says why). A set with no recordings yet is skipped: start it again when they
# arrive. Saved transcripts aren't paid for twice and Muse Spark's replies come back from the cache, so a call
# already run gives the same outcome and costs nothing; only new calls are new.
#
# Writes runs/eval-test/ (FTC and IN test: A, B, C, C-no-speakers, and C on the two transcription ablations),
# runs/eval-paraphrase/ (the people's paraphrase takes: A, B, C) and runs/eval-synth/ (synthetic voices: A, B, C),
# each with its table.md, never mixed.
set -euo pipefail
cd "$(dirname "$0")/.."
tk() { .venv/bin/teesrakaan "$@"; }
has_audio() { [ -d "$1" ] && find -L "$1" -maxdepth 1 -type f \( -iname '*.wav' -o -iname '*.m4a' -o -iname '*.mp3' \) | grep -q .; }

git rev-parse -q --verify refs/tags/eval-freeze >/dev/null || { echo "No eval-freeze tag: test sets run only after the freeze."; exit 1; }
git ls-files --error-unmatch eval/ftc-test-labels.csv >/dev/null 2>&1 && git diff --quiet HEAD -- eval/ftc-test-labels.csv \
  || { echo "Commit eval/ftc-test-labels.csv before any test run."; exit 1; }
tk labels eval/ftc-test-labels.csv
tk budget | grep -qx 'paid calls:  allowed' || { tk budget; echo "Paid calls aren't allowed now: record a Billing reading first."; exit 1; }
(cd data/synthetic/eval && sha256sum --quiet -c ../../../eval/synth-audio.sha256)
mkdir -p runs/eval-test runs/eval-paraphrase runs/eval-synth

echo "== FTC test"
tk transcribe-set data/ftc/audio-test --out data/transcripts/ftc-test
for r in A B C C-no-speakers; do
  tk eval data/transcripts/ftc-test --labels eval/ftc-test-labels.csv --split test --run "$r" --out "runs/eval-test/ftc-$r.json"
done

echo "== IN-synth (synthetic voices)"
for s in test paraphrase; do
  tk transcribe-set "data/synthetic/eval/$s" --out "data/transcripts/synth-$s"
  for r in A B C; do
    tk eval "data/transcripts/synth-$s" --labels eval/synth-labels.csv --split "$s" --run "$r" --out "runs/eval-synth/results-$s-$r.json"
  done
done
tk keywords data/transcripts/synth-paraphrase | tee runs/eval-synth/keywords-paraphrase.txt

if has_audio data/recordings/test && [ -f data/labels-in.csv ]; then
  echo "== IN test (people's recordings)"
  tk labels data/labels-in.csv
  tk transcribe-set data/recordings/test --out data/transcripts/in-test
  tk transcribe-set data/recordings/test --out data/transcripts/in-test-nolang --no-language-hint
  tk transcribe-set data/recordings/test --out data/transcripts/in-test-nokw --no-keywords
  for r in A B C C-no-speakers; do
    tk eval data/transcripts/in-test --labels data/labels-in.csv --split test --run "$r" --out "runs/eval-test/in-$r.json"
  done
  tk eval data/transcripts/in-test-nolang --labels data/labels-in.csv --split test --run C --out runs/eval-test/in-nolang-C.json
  tk eval data/transcripts/in-test-nokw --labels data/labels-in.csv --split test --run C --out runs/eval-test/in-nokw-C.json
else
  echo "== IN test: no recordings in data/recordings/test yet (or no data/labels-in.csv); skipped"
fi

if has_audio data/recordings/paraphrase && [ -f data/labels-in.csv ]; then
  echo "== Paraphrase (people's takes)"
  tk labels data/labels-in.csv
  tk transcribe-set data/recordings/paraphrase --out data/transcripts/in-paraphrase
  for r in A B C; do
    tk eval data/transcripts/in-paraphrase --labels data/labels-in.csv --split paraphrase --run "$r" --out "runs/eval-paraphrase/in-$r.json"
  done
  tk keywords data/transcripts/in-paraphrase | tee runs/eval-paraphrase/keywords.txt
  solo=$(grep -c ',paraphrase,.*solo take' data/labels-in.csv || true)
  echo "solo takes among the labelled paraphrase calls: $solo" | tee runs/eval-paraphrase/solo.txt
else
  echo "== Paraphrase: no takes in data/recordings/paraphrase yet (or no data/labels-in.csv); skipped"
fi

echo "== Tables"
tk table runs/eval-test/*.json | tee runs/eval-test/table.md
tk table runs/eval-synth/results-test-*.json | tee runs/eval-synth/table-test.md
tk table runs/eval-synth/results-paraphrase-*.json | tee runs/eval-synth/table-paraphrase.md
if ls runs/eval-paraphrase/in-*.json >/dev/null 2>&1; then
  tk table runs/eval-paraphrase/in-*.json | tee runs/eval-paraphrase/table.md
fi
tk budget
