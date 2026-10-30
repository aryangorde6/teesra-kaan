"""Muse Spark over the Meta Model API (Chat Completions), behind the $100 ledger and a response cache.

Every call reserves its worst case before it's sent and settles to the real cost.
Nothing is retried automatically: a retry is a second billed call. A cached reply
keeps the latency of the original call, so replayed timings stay honest.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import httpx

from . import config
from .budget import Ledger, meta_cap
from .judge import Completion
from .pricing import SPARK_CACHED_INPUT_PER_M, SPARK_INPUT_PER_M, SPARK_OUTPUT_PER_M, estimate_tokens

META_BASE_URL = "https://api.meta.ai/v1"
MODEL = "muse-spark-1.3"  # never the contributor tier: donated calls must not train anyone's model


def cost_usd(input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
    fresh = max(input_tokens - cached_tokens, 0)
    return (fresh * SPARK_INPUT_PER_M + cached_tokens * SPARK_CACHED_INPUT_PER_M
            + output_tokens * SPARK_OUTPUT_PER_M) / 1e6


class SparkClient:
    """A `Complete` for SparkJudge: complete(system, user, json_schema) -> Completion."""

    def __init__(
        self,
        model: str = MODEL,
        # Spark 1.3 reasons before it answers, and the reasoning counts against max_tokens: on dev (Oct 30)
        # "low" used ~400 tokens and 13 of 14 replies came back empty at 400. "minimal" (the lowest it
        # accepts) used 144-361, so the limit leaves room for the JSON after it (docs/dev-log.md).
        reasoning_effort: str | None = "minimal",
        max_output_tokens: int = 1024,
        ledger: Ledger | None = None,
        cache_dir: Path | None = None,
        http: httpx.Client | None = None,
    ) -> None:
        if model.endswith("-contributor"):
            raise ValueError("The contributor tier lets Meta train on the content; it's never used here.")
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.ledger = ledger or Ledger("meta", meta_cap())
        self.cache_dir = cache_dir if cache_dir is not None else config.data_dir() / "cache" / "spark"
        self._http = http

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                base_url=META_BASE_URL,
                headers={"Authorization": f"Bearer {config.api_key()}"},
                timeout=60,
            )
        return self._http

    def request(self, system: str, user: str, schema: dict | None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": self.max_output_tokens,
        }
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "signals", "schema": schema}}
        return body

    def _cache_path(self, body: dict) -> Path:
        key = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return self.cache_dir / key[:2] / f"{key}.json"

    def __call__(self, system: str, user: str, schema: dict | None = None) -> Completion:
        body = self.request(system, user, schema)
        cached = self._cache_path(body)
        if cached.is_file():
            return Completion(**json.loads(cached.read_text(encoding="utf-8")))

        worst = cost_usd(estimate_tokens(system + user), self.max_output_tokens)
        call_id = self.ledger.reserve(self.model, worst, note="judge")
        started = time.monotonic()
        try:
            response = self.http.post("/chat/completions", json=body)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # 4xx: rejected before any work, so not billed. 5xx: may have been.
            if exc.response.status_code >= 500:
                self.ledger.mark_unknown(call_id)
            else:
                self.ledger.release(call_id)
            raise
        except httpx.HTTPError:
            self.ledger.mark_unknown(call_id)
            raise
        latency = time.monotonic() - started

        data = response.json()
        usage = data.get("usage") or {}
        n_in = int(usage.get("prompt_tokens") or 0)
        n_out = int(usage.get("completion_tokens") or 0)
        n_cached = int((usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
        self.ledger.settle(call_id, cost_usd(n_in, n_out, n_cached), n_in, n_out, data.get("id"))

        choice = (data.get("choices") or [{}])[0]
        done = Completion((choice.get("message") or {}).get("content") or "", n_in, n_out, round(latency, 3))
        if choice.get("finish_reason") != "length":
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps(done.__dict__, ensure_ascii=False), encoding="utf-8")
        return done


class ReplayClient(SparkClient):
    """Saved replies only, never the API. The hosted page plays its demo calls with Muse Spark's real
    answers, recorded once on the development machine, so it needs no key and costs nothing."""

    def __init__(self, cache_dir: Path) -> None:
        super().__init__(ledger=_NO_LEDGER, cache_dir=cache_dir)

    def __call__(self, system: str, user: str, schema: dict | None = None) -> Completion:
        cached = self._cache_path(self.request(system, user, schema))
        if not cached.is_file():
            raise LookupError("no saved Muse Spark reply for this question")
        return Completion(**json.loads(cached.read_text(encoding="utf-8")))


_NO_LEDGER: Any = object()  # a replay never spends, so it never opens the ledger
