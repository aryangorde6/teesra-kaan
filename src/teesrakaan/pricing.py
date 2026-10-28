"""List prices, for estimating and recording what a call costs."""

from __future__ import annotations

# Meta Model API, dev.meta.ai/docs/pricing-rate-limits (checked Oct 28, 2026). USD.
SPARK_INPUT_PER_M = 1.25
SPARK_CACHED_INPUT_PER_M = 0.15
SPARK_OUTPUT_PER_M = 4.25
TRANSCRIBE_PER_HOUR = 0.18  # Muse Voice Transcribe, the same with zero data retention

BUDGET_STOP_USD = 120.0  # hard stop, of the $150 credits


def estimate_tokens(text: str) -> int:
    """Upper-side estimate: about 3 characters per token, plus a margin. Devanagari runs higher."""
    return len(text) // 3 + 64


def call_cost(audio_seconds: float, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> float:
    fresh = max(input_tokens - cached_input_tokens, 0)
    return (
        audio_seconds / 3600 * TRANSCRIBE_PER_HOUR
        + fresh * SPARK_INPUT_PER_M / 1e6
        + cached_input_tokens * SPARK_CACHED_INPUT_PER_M / 1e6
        + output_tokens * SPARK_OUTPUT_PER_M / 1e6
    )
