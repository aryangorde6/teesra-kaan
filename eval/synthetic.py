"""The synthetic set (docs/evaluation-rule.md, "The synthetic set"): synthetic voices, not people.

The Hindi, Marathi and English test scripts and the paraphrase scripts, spoken by Kokoro v1.0 with one voice
for the caller and another for the listener, then passed through a phone band with light noise. It is the
pipeline of the synthetic pre-check on dev (docs/dev-log.md, Oct 30), unchanged.

Not part of the package: run it with any Python that has kokoro-onnx and numpy, with ffmpeg on the PATH.

    python eval/synthetic.py <dir with kokoro-v1.0.onnx and voices-v1.0.bin> <out dir>

Writes <out>/test/<ID>.wav and <out>/paraphrase/<ID>.wav (16 kHz mono) and <out>/manifest.json, which has every
line's start and end in seconds.
"""
import csv
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from kokoro_onnx import Kokoro

REPO = Path(__file__).resolve().parents[1]
MODELS, OUT = Path(sys.argv[1]), Path(sys.argv[2])
GAP = 0.6  # seconds between turns, as in teesrakaan.scripts.to_call
LEAD = 0.5  # seconds before the first turn
LANGS = {"hi": "hi", "mr": "mr", "en": "en-us"}  # Hinglish is in Latin letters, which the Hindi voices can't read
VOICES = {  # (male, female) per language; Kokoro has no Marathi voice, so Marathi is read by a Hindi one
    "hi": ("hm_omega", "hf_alpha"), "mr": ("hm_omega", "hf_alpha"), "en": ("am_michael", "af_heart")}
ALT = {"hi": ("hm_psi", "hf_beta"), "mr": ("hm_psi", "hf_beta"), "en": ("am_adam", "af_bella")}  # same gender
FEMALE = ("woman", "mother", "girl", "daughter", "aunt", "lady", "wife", "she ", "her ", "sister", "maa")
FEMALE_HI = ("बोलतेय", "बोल रही", "बोलते आहे", "बोलत आहे", "मी सायली", "वर्गशिक्षिका")


def is_female(role: str, first_line: str) -> bool:
    role = f" {role.lower()} "
    return any(w in role for w in FEMALE) or any(w in first_line for w in FEMALE_HI)


def scripts():
    """(split, script) for every script in the set, in a fixed order."""
    with open(REPO / "eval/scripts/split.csv", newline="", encoding="utf-8") as f:
        split = {r["id"]: r["split"] for r in csv.DictReader(f)}
    for name in ("in-scam.json", "in-genuine.json", "in-paraphrase.json"):
        data = json.loads((REPO / "eval/scripts" / name).read_text(encoding="utf-8"))
        for s in data["scripts"]:
            where = "paraphrase" if name == "in-paraphrase.json" else split[s["id"]]
            if where in ("test", "paraphrase") and s["language"] in LANGS:
                yield where, {**s, "set": data["set"]}


def main() -> None:
    kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    manifest = {}
    for where, s in scripts():
        lang, roles = s["language"], s.get("roles", {})
        caller_lines = [t for who, t, *_ in s["lines"] if who == "caller"]
        listener_lines = [t for who, t, *_ in s["lines"] if who == "listener"]
        cf = is_female(roles.get("caller", ""), caller_lines[0] if caller_lines else "")
        lf = is_female(roles.get("listener", ""), listener_lines[0] if listener_lines else "")
        voice = {"caller": VOICES[lang][int(cf)]}
        voice["listener"] = (ALT if cf == lf else VOICES)[lang][int(lf)]
        pieces, t, lines = [np.zeros(int(LEAD * 24000), dtype=np.float32)], LEAD, []
        for who, text, *_ in s["lines"]:
            samples, sr = kokoro.create(text, voice=voice[who], speed=1.0, lang=LANGS[lang])
            assert sr == 24000
            dur = len(samples) / sr
            lines.append({"speaker": who, "start": round(t, 2), "end": round(t + dur, 2), "text": text})
            pieces += [samples, np.zeros(int(GAP * sr), dtype=np.float32)]
            t += dur + GAP
        audio = np.concatenate(pieces)
        clean_dir, phone_dir = OUT / f"clean-{where}", OUT / where
        clean_dir.mkdir(parents=True, exist_ok=True)
        phone_dir.mkdir(parents=True, exist_ok=True)
        clean = clean_dir / f"{s['id']}.wav"
        with wave.open(str(clean), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
        # Phone band (300-3400 Hz through 8 kHz) plus light pink noise: closer to a call on speaker.
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(clean), "-filter_complex",
                        "[0]highpass=f=300,lowpass=f=3400,aresample=8000,aresample=16000[a];"
                        "anoisesrc=color=pink:amplitude=0.012:r=16000:seed=7[n];"
                        "[a][n]amix=inputs=2:duration=first:normalize=0",
                        "-ac", "1", "-ar", "16000", str(phone_dir / f"{s['id']}.wav")], check=True)
        manifest[s["id"]] = {"split": where, "set": s["set"], "language": lang, "pattern": s.get("pattern", 0),
                             "voices": voice, "duration": round(len(audio) / 24000, 2), "lines": lines}
        print(s["id"], where, lang, voice, f"{len(audio) / 24000:.1f} s", flush=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(manifest), "calls,", round(sum(m["duration"] for m in manifest.values()) / 60, 1), "min")


if __name__ == "__main__":
    main()
