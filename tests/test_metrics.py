import pytest

from teesrakaan.metrics import Outcome, naive_came_true, percentile, rate, summarize, summarize_by, wilson


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


def test_results_table_has_a_row_per_run():
    from teesrakaan.metrics import results_table

    s = summarize([Outcome("s1", "IN-scam", True, 2, t_warn=20, t0=5, t_ask=50), Outcome("g1", "IN-scam", False, 0)])
    table = results_table([{"run": "A", "split": "dev", "by_set": {"IN-scam": s}},
                           {"run": "C", "split": "dev", "by_set": {"IN-scam": s}}])
    assert "| A | 1/1" in table and "| C | 1/1" in table and "15 s" in table
    assert "The next line, **IN-scam**" in table


def test_results_table_shows_amber_false_alarms_and_the_90th_percentile():
    from teesrakaan.metrics import results_table

    s = summarize([Outcome("s1", "IN-scam", True, 2, t_warn=20, t_red=30, t0=5),
                   Outcome("g1", "IN-genuine", False, 1), Outcome("g2", "IN-genuine", False, 0)])
    row = results_table([{"run": "C", "split": "test", "by_set": {"IN-scam": s}}]).splitlines()[4]
    cells = [c.strip() for c in row.strip("|").split("|")]
    assert cells[3].startswith("0/2") and cells[4].startswith("1/2")  # red, then amber false alarms
    assert cells[5] == "15 s (15 s)" and cells[6] == "25 s"


def test_results_files_from_before_the_next_line_have_no_next_line_block():
    from teesrakaan.metrics import results_table

    s = summarize([Outcome("s1", "IN-scam", True, 2, t_warn=20, t0=5, t_ask=50)])
    del s["next_line"]
    assert "The next line" not in results_table([{"run": "A", "split": "dev", "by_set": {"IN-scam": s}}])


def test_next_line_counts_what_came_true_how_early_and_on_which_calls():
    rows = [
        Outcome("s1", "IN-scam", True, 2, predictions=(("A4", 20.0, 31.0), ("A6", 35.0, None))),
        Outcome("s2", "IN-scam", True, 1),
        Outcome("g1", "IN-genuine", False, 0, predictions=(("A6", 40.0, None),)),
    ]
    n = summarize(rows)["next_line"]
    assert n["shown"] == 3 and n["came_true"]["k"] == 1 and n["came_true"]["n"] == 3
    assert n["seconds_ahead"]["median"] == 11
    assert n["reach"]["k"] == 1 and n["reach"]["n"] == 2  # scam calls only
    assert n["per_genuine_call"] == {"shown": 1, "calls": 1, "mean": 1.0}
    assert n["naive_guess"] is None  # dev only, asked for


def test_the_naive_guess_names_the_commonest_signal_not_yet_found():
    # A1 and A6 are on both calls. When each prediction is shown, A1 has been found, so the guess is A6:
    # on s1 the caller says it after (it came true), on s2 before (it doesn't count).
    rows = [
        Outcome("s1", "IN-scam", True, 2, predictions=(("A4", 10.0, None),),
                found=(("A1", 2.0, 4.0), ("A6", 12.0, 14.0))),
        Outcome("s2", "IN-scam", True, 2, predictions=(("A4", 5.0, 9.0),),
                found=(("A1", 1.0, 3.0), ("A6", 2.0, 6.0), ("A4", 9.0, 11.0))),
    ]
    assert naive_came_true(rows) == 1
    n = summarize(rows, naive=True)["next_line"]
    assert n["naive_guess"]["k"] == 1 and n["came_true"]["k"] == 1
