"""The listener's lines for solo takes of the paraphrase cards (docs/evaluation-rule.md, Robustness, "Solo takes")
and, since v1.6.1, of the test cards ("People's recordings after the freeze").

One person says the caller's lines; the studio lays these into the take between them (since v1.6.1; before, it
played them through the laptop's speaker). Spoken by Kokoro v1.0 with the synthetic set's main Hindi or English
voice of the listener's gender, as the script's roles give it, or, for a card without roles, the verb forms of the
listener's first line (male otherwise). Marathi is read by the Hindi voice, as in the synthetic set (Kokoro has no
Marathi voice). Kokoro's Hindi voices can't read Latin letters, so the Hinglish listener lines are spelled in
Devanagari for it: the same words (IP37's still none of the keyword lists', tests/test_paraphrase.py). Cards already
in eval/solo-listener.json with their audio are left as they are.

Not part of the package: run it with any Python that has kokoro-onnx and numpy.

    python eval/solo_listener.py <dir with kokoro-v1.0.onnx and voices-v1.0.bin> [out dir, default data/solo]

Writes <out>/<ID>/<n>.wav (24 kHz mono; n is the line's index in the script) and eval/solo-listener.json, which has
each file's text, voice, length and SHA-256.
"""
import csv
import hashlib
import json
import sys
import wave
from pathlib import Path

import numpy as np
from kokoro_onnx import Kokoro

REPO = Path(__file__).resolve().parents[1]
MODELS = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / "data" / "solo"
LANGS = {"hi": "hi", "mr": "mr", "en": "en-us", "hi+en": "hi"}
VOICES = {"hi": ("hm_omega", "hf_alpha"), "mr": ("hm_omega", "hf_alpha"), "en": ("am_michael", "af_heart"),
          "hi+en": ("hm_omega", "hf_alpha")}  # (male, female): the synthetic set's main voices
FEMALE = ("woman", "widow", "homemaker", "mother", "girl", "lady", "wife", "daughter", "sister")
FEMALE_HI = ("बोलतेय", "बोल रही", "बोलते आहे", "बोलत आहे", "मी सायली", "वर्गशिक्षिका")  # as eval/synthetic.py
SPELLED = {  # Hinglish, in Devanagari for the Hindi voice: the same words
    ("IP37", 1): "मैंने तो ऑनलाइन कर दिया था।",  # "Maine toh online kar diya tha."
    ("IS03", 1): "अच्छा? मैंने तो ब्रांच में सब जमा किया था।",
    ("IS03", 3): "तो क्या करना होगा?",
    ("IS07", 1): "हाँ, मेरा ऑर्डर कैंसल हुआ था, 640 रुपये का।",
    ("IS07", 4): "इतना सब क्यों?",
    ("IS14", 2): "मेरा तो एक ही नंबर है।",
    ("IS20", 1): "सच में? कैसे?",
    ("IS30", 1): "हाँ, मेरा एक दोस्त है लंदन में।",
    ("IS37", 1): "मैंने तो ऑनलाइन भरा था।",
    ("IG07", 1): "हाँ, अकाउंट में बैलेंस है।",
    ("IG18", 1): "बस दो मिनट।",
    ("IG23", 1): "ठीक है, कितने बजे?",
}


def cards() -> list[dict]:
    """The paraphrase cards, then the test cards, each in ID order."""
    with open(REPO / "eval/scripts/split.csv", newline="", encoding="utf-8") as f:
        split = {r["id"]: r["split"] for r in csv.DictReader(f)}
    out = json.loads((REPO / "eval/scripts/in-paraphrase.json").read_text(encoding="utf-8"))["scripts"]
    for name in ("in-scam.json", "in-genuine.json"):
        out += [s for s in json.loads((REPO / "eval/scripts" / name).read_text(encoding="utf-8"))["scripts"]
                if split[s["id"]] == "test"]
    return out


def is_female(s: dict) -> bool:
    listener = [text for who, text, *_ in s["lines"] if who == "listener"]
    role = s.get("roles", {}).get("listener", "").lower()
    return any(w in role for w in FEMALE) or any(w in (listener[0] if listener else "") for w in FEMALE_HI)


def main() -> None:
    kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    manifest = REPO / "eval/solo-listener.json"
    made = json.loads(manifest.read_text(encoding="utf-8"))["cards"] if manifest.exists() else {}
    done = {}
    for s in cards():
        old = made.get(s["id"])
        if old and all((OUT / s["id"] / f"{n}.wav").exists() for n in old["lines"]):
            done[s["id"]] = old
            continue
        lang = s["language"]
        voice = VOICES[lang][int(is_female(s))]
        lines = {}
        for n, (who, text, *_) in enumerate(s["lines"]):
            if who != "listener":
                continue
            spoken = SPELLED.get((s["id"], n), text)
            samples, sr = kokoro.create(spoken, voice=voice, speed=1.0, lang=LANGS[lang])
            path = OUT / s["id"] / f"{n}.wav"
            path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes((np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes())
            lines[str(n)] = {"text": text, **({"spoken_as": spoken} if spoken != text else {}),
                             "seconds": round(len(samples) / sr, 2), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        done[s["id"]] = {"language": lang, "voice": voice, "lines": lines}
        print(s["id"], lang, voice, len(lines), "lines", flush=True)
    out = {"about": "The listener's lines in solo takes of the paraphrase and test cards (docs/evaluation-rule.md, "
                    "Robustness and People's recordings after the freeze). Kokoro v1.0 (Apache 2.0), made by "
                    "eval/solo_listener.py; the audio stays in data/solo/.",
           "cards": done}
    manifest.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
