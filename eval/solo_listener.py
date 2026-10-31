"""The listener's lines for solo takes of the paraphrase cards (docs/evaluation-rule.md, Robustness, "Solo takes").

One person reads the caller's lines as written; the studio plays these between them through the laptop's speaker.
Spoken by Kokoro v1.0 with the synthetic set's main Hindi or English voice of the listener's gender, as the script's
roles give it. Marathi is read by the Hindi voice, as in the synthetic set (Kokoro has no Marathi voice). Kokoro's
Hindi voices can't read Latin letters, so IP37's one listener line (Hinglish) is spelled in Devanagari: the same
words, and still none of the keyword lists' (tests/test_paraphrase.py).

Not part of the package: run it with any Python that has kokoro-onnx and numpy.

    python eval/solo_listener.py <dir with kokoro-v1.0.onnx and voices-v1.0.bin> [out dir, default data/solo]

Writes <out>/<ID>/<n>.wav (24 kHz mono; n is the line's index in the script) and eval/solo-listener.json, which has
each file's text, voice, length and SHA-256.
"""
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
SPELLED = {("IP37", 1): "मैंने तो ऑनलाइन कर दिया था।"}  # "Maine toh online kar diya tha."


def main() -> None:
    kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    scripts = json.loads((REPO / "eval/scripts/in-paraphrase.json").read_text(encoding="utf-8"))["scripts"]
    cards = {}
    for s in scripts:
        lang = s["language"]
        female = any(w in s["roles"]["listener"].lower() for w in FEMALE)
        voice = VOICES[lang][int(female)]
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
        cards[s["id"]] = {"language": lang, "voice": voice, "lines": lines}
        print(s["id"], lang, voice, len(lines), "lines", flush=True)
    out = {"about": "The listener's lines played in solo takes of the paraphrase cards (docs/evaluation-rule.md, "
                    "Robustness). Kokoro v1.0 (Apache 2.0), made by eval/solo_listener.py; the audio stays in data/solo/.",
           "cards": cards}
    (REPO / "eval/solo-listener.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
