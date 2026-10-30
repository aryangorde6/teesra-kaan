from pathlib import Path

import pytest

from teesrakaan.transcript import load_call

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "calls"


@pytest.fixture
def example():
    """Loads one of the written demo calls in examples/calls by name."""
    return lambda name: load_call(EXAMPLES / f"{name}.json")


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch, tmp_path):
    """Tests never see a real key or the real data folder, so nothing can reach a paid API."""
    for name in ("MODEL_API_KEY", "TEESRAKAAN_ALLOW_PAID", "TEESRAKAAN_BUDGET_META_USD", "TEESRAKAAN_ASR_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TEESRAKAAN_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("TEESRAKAAN_VOICE", str(tmp_path / "voice"))
    # A real .env (key, paid calls on) must never leak into a test.
    monkeypatch.setattr("teesrakaan.config.load_dotenv", lambda path=None: None)
