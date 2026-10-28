from pathlib import Path

import pytest

from teesrakaan.transcript import load_call

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "calls"


@pytest.fixture
def example():
    """Loads one of the written demo calls in examples/calls by name."""
    return lambda name: load_call(EXAMPLES / f"{name}.json")


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """Tests never see a real key, so nothing can reach a paid API."""
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
