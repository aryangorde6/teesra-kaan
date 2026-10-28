import asyncio
import json

import httpx
import pytest

from teesrakaan.asr import BYTES_PER_SECOND, handshake, session_to_call, stream
from teesrakaan.budget import BudgetExceeded, Ledger, PaidCallsDisabled
from teesrakaan.judge import SPARK_SCHEMA_V1
from teesrakaan.keywords import KeywordJudge
from teesrakaan.signals import Level
from teesrakaan.simulate import Timing, simulate
from teesrakaan.spark import SparkClient

serve = pytest.importorskip("websockets.asyncio.server").serve

# What a diarized realtime session sends, per dev.meta.ai/docs/speech-to-text.
SCRIPT = [
    {"type": "speechStart", "turnId": 1, "audioProcessedMs": 100},
    {"type": "speaker", "label": "A", "audioProcessedMs": 300},
    {"type": "transcript", "transcript": "Hello", "final": False, "audioProcessedMs": 400},
    {"type": "speechComplete", "turnId": 1, "transcript": "Hello?", "audioProcessedMs": 600},
    {"type": "speechStart", "turnId": 2, "audioProcessedMs": 700},
    {"type": "speaker", "label": "B", "audioProcessedMs": 800},
    {"type": "transcript", "transcript": "Main crime branch se", "final": False, "audioProcessedMs": 1200},
    {"type": "transcript", "transcript": "Main crime branch se bol raha hoon. Aapke naam pe FIR darj hai.",
     "final": False, "audioProcessedMs": 2500},
    {"type": "speechEnd", "turnId": 2, "audioProcessedMs": 2700},
    {"type": "speechComplete", "turnId": 2,
     "transcript": "Main crime branch se bol raha hoon. Aapke naam pe FIR darj hai. Kisi ko mat batana.",
     "audioProcessedMs": 3000},
]


async def fake_server(ws):
    first = json.loads(await ws.recv())
    assert first["authorization"]["accessToken"] == "Bearer test-key" and first["mode"] == "DIARIZATION"
    await ws.send(json.dumps({"sessionId": "s-1"}))
    sent = False
    async for frame in ws:
        if isinstance(frame, bytes) and not sent:
            for event in SCRIPT:
                await ws.send(json.dumps(event))
            sent = True
        elif isinstance(frame, str) and json.loads(frame).get("type") == "endStream":
            await ws.close(1000)
            return


def test_stream_collects_events_and_becomes_a_call():
    async def run():
        async with serve(fake_server, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            pcm = b"\0" * int(BYTES_PER_SECOND * 0.3)
            return await stream(pcm, handshake("test-key"), url=f"ws://127.0.0.1:{port}")

    session = asyncio.run(run())
    assert session.session_id == "s-1" and "authorization" not in session.settings
    assert len(session.events) == len(SCRIPT) and all("received" in e for e in session.events)

    call = session_to_call(session, "fake")
    assert [t.speaker for t in call.turns] == ["A", "B"] and call.caller_label() == "B"
    assert call.turns[1].text.endswith("Kisi ko mat batana.")
    assert len(call.turns[1].heard_times) == len(call.turns[1].text.split())

    result = simulate(call, KeywordJudge(), Timing(judge_latency=0.5))
    assert result.level == Level.RED  # authority + threat + isolation
    assert "Hello" not in " ".join(f.quote for f in result.listener.found.values())


def test_spark_client_reserves_settles_and_caches(tmp_path, monkeypatch):
    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "r1",
            "choices": [{"message": {"content": '{"yes": []}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 20, "prompt_tokens_details": {"cached_tokens": 800}},
        })

    ledger = Ledger("meta", 120.0, tmp_path / "budget.sqlite")
    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.meta.ai/v1")
    client = SparkClient(ledger=ledger, cache_dir=tmp_path / "cache", http=http)
    first = client("system", "user", SPARK_SCHEMA_V1)
    again = client("system", "user", SPARK_SCHEMA_V1)
    assert len(seen) == 1 and first == again and first.latency is not None
    assert seen[0]["model"] == "muse-spark-1.3" and seen[0]["response_format"]["type"] == "json_schema"
    summary = ledger.summary()
    assert summary.calls == 1 and summary.spent_usd == pytest.approx((200 * 1.25 + 800 * 0.15 + 20 * 4.25) / 1e6)


def test_paid_calls_are_off_unless_allowed(tmp_path):
    client = SparkClient(ledger=Ledger("meta", 120.0, tmp_path / "b.sqlite"), cache_dir=tmp_path / "c",
                         http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    with pytest.raises(PaidCallsDisabled):
        client("s", "u", None)


def test_the_meta_cap_never_goes_above_120(tmp_path, monkeypatch):
    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    ledger = Ledger("meta", 500.0, tmp_path / "b.sqlite")
    assert ledger.cap_usd == 120.0
    with pytest.raises(BudgetExceeded):
        ledger.reserve("muse-spark-1.3", 121.0)


def test_contributor_tier_is_refused():
    with pytest.raises(ValueError):
        SparkClient(model="muse-spark-1.3-contributor")
