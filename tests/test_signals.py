import pytest

from teesrakaan.signals import ASKS, BY_ID, FLAGS, SIGNALS, Level, decide


def test_twelve_signals_split_into_asks_and_flags():
    assert [s.id for s in SIGNALS] == [f"A{i}" for i in range(1, 13)]
    assert ASKS == {"A5", "A6", "A7", "A11"}
    assert ASKS | FLAGS == BY_ID.keys() and not ASKS & FLAGS


@pytest.mark.parametrize("sid", [s.id for s in SIGNALS])
def test_never_on_one_signal_alone(sid):
    assert decide({sid}).level == Level.NONE


def test_nothing_heard_is_no_alarm():
    assert decide(set()).level == Level.NONE


def test_an_ask_with_any_other_signal_is_red():
    alarm = decide({"A1", "A5"})  # "I'm from the bank" + "tell me the OTP"
    assert alarm.level == Level.RED and alarm.rule == "ask"
    assert decide({"A6", "A11"}).level == Level.RED  # pattern 5: PIN to receive a refund
    assert decide({"A6", "A12"}).level == Level.RED  # pattern 9: pay a fee to claim a prize
    assert decide({"A5", "A8"}).level == Level.RED  # OTP, then "come on WhatsApp"


def test_digital_arrest_opening_is_red_before_any_ask():
    alarm = decide({"A1", "A2", "A4"})
    assert alarm.level == Level.RED and alarm.rule == "digital-arrest opening"


def test_two_flags_are_amber():
    alarm = decide({"A1", "A9"})  # "customs officer" + "drugs in your parcel"
    assert alarm.level == Level.AMBER and alarm.rule == "two flags"
    assert decide({"A1", "A2", "A3"}).level == Level.AMBER


def test_unknown_ids_are_ignored():
    assert decide({"A1", "Z9"}).level == Level.NONE


def test_more_signals_never_lower_the_level():
    found: set[str] = set()
    last = Level.NONE
    for sid in ["A3", "A9", "A1", "A2", "A4", "A8", "A6"]:
        found.add(sid)
        level = decide(found).level
        assert level >= last
        last = level
    assert last == Level.RED


# The signal sequence of each pattern in docs/scam-tactics.md, opening → ask.
PATTERNS = {
    1: "A1 A2 A4 A8 A6",
    2: "A9 A10 A1 A2",
    3: "A1 A2 A3 A10 A5",
    4: "A1 A2 A3 A5 A7",
    5: "A12 A6 A11",
    6: "A1 A12 A7 A5 A6",
    7: "A2 A3 A4 A6",
    8: "A1 A2 A3 A6 A7",
    9: "A12 A6",
}


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_every_documented_pattern_warns_and_goes_red_once_it_asks(pattern):
    signals = PATTERNS[pattern].split()
    assert decide(signals).level >= Level.AMBER
    if ASKS & set(signals):
        assert decide(signals).level == Level.RED
