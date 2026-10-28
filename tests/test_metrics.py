import pytest

from teesrakaan.metrics import Outcome, percentile, rate, summarize, summarize_by, wilson


def test_wilson_matches_the_example_in_the_evaluation_rule():
    lo, hi = wilson(9, 10)
    assert lo == pytest.approx(0.596, abs=1e-3) and hi == pytest.approx(0.982, abs=1e-3)
    assert rate(9, 10) == "9/10 (60–98%)"


def test_wilson_edges():
    assert wilson(0, 0) == (0.0, 1.0)
    assert wilson(0, 10)[0] == 0.0 and wilson(10, 10)[1] == pytest.approx(1.0)
    assert rate(0, 0) == "0/0"


def test_percentile_interpolates():
    assert percentile([], 0.5) is None
    assert percentile([4.0], 0.9) == 4.0
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 0.9) == pytest.approx(91.0)


def test_summary_counts_catches_false_alarms_and_timing():
    rows = [
        Outcome("s1", "IN-scam", True, 2, t_warn=20, t_red=40, t0=5, t_ask=50),
        Outcome("s2", "IN-scam", True, 1, t_warn=30, t0=10, t_ask=25),
        Outcome("s3", "IN-scam", True, 0, t0=3),
        Outcome("g1", "IN-genuine", False, 1, t_warn=12),
        Outcome("g2", "IN-genuine", False, 0),
    ]
    s = summarize(rows)
    assert s["caught_red"]["k"] == 1 and s["caught_red_or_amber"]["k"] == 2 and s["scam_calls"] == 3
    assert s["false_alarms_red"]["k"] == 0 and s["false_alarms_amber"]["k"] == 1
    assert s["seconds_to_warning"] == {"n": 2, "median": 17.5, "p90": pytest.approx(19.5)}
    assert s["seconds_to_red"]["median"] == 35
    assert s["warned_before_ask"]["k"] == 1 and s["warned_before_ask"]["n"] == 2


def test_sets_are_never_pooled():
    rows = [Outcome("a", "FTC", True, 2), Outcome("b", "IN-scam", True, 0)]
    by_set = summarize_by(rows, "set")
    assert set(by_set) == {"FTC", "IN-scam"}
    assert by_set["FTC"]["caught_red"]["k"] == 1 and by_set["IN-scam"]["caught_red"]["k"] == 0
