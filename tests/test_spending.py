"""The three spending checks of budget.py: our own count, Meta's meter, and the date."""

import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from teesrakaan.budget import PAID_UNTIL, BudgetExceeded, Ledger, paid_until

SRC = Path(__file__).resolve().parent.parent / "src" / "teesrakaan"


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    return Ledger("meta", 100.0, tmp_path / "b.sqlite")


def spend(ledger, usd):
    ledger.settle(ledger.reserve("muse-spark-1.3", usd), usd)


def test_nothing_is_paid_for_until_metas_meter_is_read(ledger):
    with pytest.raises(BudgetExceeded, match="meter hasn't been read"):
        ledger.reserve("muse-spark-1.3", 0.01)
    ledger.record_meter(150.0, 0.0, "test")
    spend(ledger, 0.01)


def test_a_balance_on_metas_billing_page_stops_everything(ledger):
    ledger.record_meter(150.0, 0.0, "test")
    spend(ledger, 1.0)
    ledger.record_meter(149.0, 12.5, "test")
    with pytest.raises(BudgetExceeded, match="card is being billed"):
        ledger.reserve("muse-spark-1.3", 0.01)
    assert ledger.summary().refusal


def test_the_meter_is_read_again_every_10_dollars_and_every_day(ledger):
    ledger.record_meter(150.0, 0.0, "test")
    spend(ledger, 9.5)
    with pytest.raises(BudgetExceeded, match="every \\$10"):
        ledger.reserve("muse-spark-1.3", 1.0)
    ledger.record_meter(141.0, 0.0, "test")
    spend(ledger, 1.0)
    ledger.record_meter(140.0, 0.0, "test", ts=time.time() - 25 * 3600)
    with pytest.raises(BudgetExceeded, match="24 hours"):
        ledger.reserve("muse-spark-1.3", 0.01)


def test_metas_meter_ahead_of_the_ledger_means_something_spends_outside_it(ledger):
    ledger.record_meter(140.0, 0.0, "test")  # $10 spent, none of it through the ledger
    with pytest.raises(BudgetExceeded, match="outside it"):
        ledger.reserve("muse-spark-1.3", 0.01)
    ledger.record_meter(140.0, 0.0, "test", drift_ok=True)
    spend(ledger, 2.0)
    assert ledger.summary().counted_usd == pytest.approx(12.0)  # Meta's $10 plus our $2 since


def test_the_higher_count_is_the_one_held_against_the_stop(tmp_path, monkeypatch):
    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    ledger = Ledger("meta", 20.0, tmp_path / "b.sqlite")
    ledger.record_meter(150.0, 0.0, "test")
    spend(ledger, 8.0)
    ledger.record_meter(138.0, 0.0, "test")  # Meta counts $12 against our $8: within the $5 drift
    spend(ledger, 7.0)
    assert ledger.summary().counted_usd == pytest.approx(19.0)
    with pytest.raises(BudgetExceeded, match="pass the \\$20.00 cap"):
        ledger.reserve("muse-spark-1.3", 1.5)


def test_the_stop_is_100_dollars_whatever_the_config_says(tmp_path, monkeypatch):
    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    monkeypatch.setenv("TEESRAKAAN_BUDGET_META_USD", "149")
    from teesrakaan.budget import meta_cap

    assert meta_cap() == 100.0 and Ledger("meta", 149.0, tmp_path / "b.sqlite").cap_usd == 100.0
    ledger = Ledger("meta", 149.0, tmp_path / "b.sqlite")
    for _ in range(10):  # $99.90 through the ledger, Meta's meter read every $9.99
        ledger.record_meter(150.0 - ledger.summary().spent_usd, 0.0, "test")
        spend(ledger, 9.99)
    ledger.record_meter(150.0 - 99.9, 0.0, "test")
    with pytest.raises(BudgetExceeded, match="cap"):
        ledger.reserve("muse-spark-1.3", 0.2)


def test_a_call_that_may_have_been_billed_counts_as_spent(ledger):
    ledger.record_meter(150.0, 0.0, "test")
    ledger.mark_unknown(ledger.reserve("muse-spark-1.3", 0.5))
    ledger.release(ledger.reserve("muse-spark-1.3", 0.5))  # refused before any work: not billed
    assert ledger.summary().spent_usd == pytest.approx(0.5)


def test_the_web_page_spends_only_its_own_share(tmp_path, monkeypatch):
    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    path = tmp_path / "b.sqlite"
    web = Ledger("meta", 100.0, path, scope="web", scope_cap_usd=5.0)
    web.record_meter(150.0, 0.0, "test")
    spend(web, 4.5)
    with pytest.raises(BudgetExceeded, match="web"):
        web.reserve("muse-spark-1.3", 1.0)
    spend(Ledger("meta", 100.0, path), 1.0)  # the evaluation still can


def test_paid_calls_end_before_the_credits_window_can(ledger, monkeypatch):
    ledger.record_meter(150.0, 0.0, "test")
    monkeypatch.setenv("TEESRAKAAN_PAID_UNTIL", "2026-10-01T00:00+00:00")
    with pytest.raises(BudgetExceeded, match="ended"):
        ledger.reserve("muse-spark-1.3", 0.01)
    monkeypatch.setenv("TEESRAKAAN_PAID_UNTIL", "2027-01-01T00:00+00:00")  # config can only make it earlier
    assert paid_until() == PAID_UNTIL == datetime(2026, 11, 4, 18, 30, tzinfo=timezone.utc)
    monkeypatch.setenv("TEESRAKAAN_PAID_UNTIL", "2026-11-03T12:00")
    with pytest.raises(ValueError):
        paid_until()


def test_a_reading_must_be_one_the_billing_page_could_show(ledger):
    with pytest.raises(ValueError):
        ledger.record_meter(151.0, 0.0)
    with pytest.raises(ValueError):
        ledger.record_meter(150.0, -1.0)


def test_every_module_that_sends_the_key_reserves_first():
    """No path to the Meta API around the ledger: any file that reads the key also reserves."""
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "api_key()" in text and path.name != "config.py":
            uses = len(re.findall(r"api_key\(\)", text))
            reserves = len(re.findall(r"\.reserve\(", text))
            assert reserves >= 1, f"{path.name} reads the key but never reserves"
            assert uses <= reserves + 1, f"{path.name}: {uses} uses of the key, only {reserves} reservations"


def test_the_meter_command_records_and_reports(tmp_path, monkeypatch, capsys):
    from teesrakaan.cli import main

    monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1")
    main(["meter", "--credits-left", "150", "--balance-inr", "0", "--source", "test"])
    out = capsys.readouterr().out
    assert "$150.00 of $150 credits left" in out and "paid calls:  allowed" in out
    main(["meter", "--credits-left", "149", "--balance-inr", "5"])
    assert "REFUSED" in capsys.readouterr().out


def test_the_paid_switch_in_dotenv_is_seen_before_any_key_is_needed(monkeypatch):
    """TEESRAKAAN_ALLOW_PAID=1 in .env must count; it used to be read only once the key was."""
    from teesrakaan import config

    monkeypatch.setattr(config, "load_dotenv", lambda path=None: monkeypatch.setenv("TEESRAKAAN_ALLOW_PAID", "1"))
    assert config.paid_calls_allowed()
