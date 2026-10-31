"""Dev only: the dev paraphrase scripts (eval/scripts/in-paraphrase-dev.json) spoken through eval/synthetic.py's
pipeline, unchanged (the same voices, phone band and noise), into a folder of their own. Hinglish is left out, as in
the synthetic set. Synthetic voices, not people; never a test result.

    python eval/synthetic_dev_paraphrase.py <dir with kokoro-v1.0.onnx and voices-v1.0.bin> data/synthetic/dev-paraphrase
"""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("synthetic", Path(__file__).resolve().parent / "synthetic.py")
synthetic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(synthetic)  # takes the models and the out dir from the command line, as when run itself


def dev_paraphrases():
    data = json.loads((synthetic.REPO / "eval/scripts/in-paraphrase-dev.json").read_text(encoding="utf-8"))
    for s in data["scripts"]:
        if s["language"] in synthetic.LANGS:
            yield "dev-paraphrase", {**s, "set": data["set"]}


synthetic.scripts = dev_paraphrases
synthetic.main()
