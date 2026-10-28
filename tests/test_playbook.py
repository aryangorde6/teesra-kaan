import re
from pathlib import Path

from teesrakaan.keywords import KeywordJudge
from teesrakaan.listener import Listener
from teesrakaan.messages import LANGS, NEXT_LINE, came_true, next_line
from teesrakaan.playbook import SCRIPTS, predict
from teesrakaan.signals import BY_ID
from teesrakaan.transcript import CALLER

DOCS = Path(__file__).resolve().parent.parent / "docs"


def test_every_script_is_a_pattern_from_the_tactics_doc_with_known_signals():
    patterns = {int(n) for n in re.findall(r"^\| (\d) \| \*\*", (DOCS / "scam-tactics.md").read_text(), re.M)}
    assert {s.pattern for s in SCRIPTS} == patterns
    for s in SCRIPTS:
        assert set(s.steps) <= BY_ID.keys() and len(set(s.steps)) == len(s.steps)


def test_one_step_never_predicts():
    assert predict({"A1"}) is None
    assert predict(set()) is None


def test_waits_while_the_scripts_disagree():
    # "Police" + "FIR": a digital arrest moves to a video call, a KYC or number-block call to a deadline.
    assert predict({"A1", "A2"}) is None


def test_digital_arrest_predicts_secrecy_after_the_video_call():
    nxt = predict({"A1", "A2", "A8"})
    assert nxt.step == "A4"
    assert set(nxt.scripts) == {"digital-arrest", "parcel"}


def test_the_ask_comes_last():
    assert predict({"A1", "A2", "A8", "A4"}).step == "A6"
    assert predict({"A1", "A2", "A8", "A4", "A6"}) is None  # the script has run out


def test_fake_customer_care_predicts_the_app():
    assert predict({"A1", "A12"}).step == "A7"


def test_a_finished_script_still_blocks_a_guess():
    # "You've won" + "pay the fee" is the whole prize script, or the start of a PIN-to-receive one.
    assert predict({"A12", "A6"}) is None


def test_every_signal_has_a_next_line_in_every_language():
    for sid in BY_ID:
        for lang in LANGS:
            assert NEXT_LINE[sid][lang].strip()
            assert next_line(sid, lang)["line"] == NEXT_LINE[sid][lang]
    assert "kisi ko mat batana" in came_true("A4", "kisi ko mat batana", "hi")["text"]


def _listen(listener, t, text):
    for w in text.split():
        listener.hear(t, CALLER, w)
        t += 0.4
    return listener.check(t, latency=1.0), t + 1.0


def test_the_listener_shows_the_next_line_and_marks_it_when_the_caller_says_it():
    listener = Listener(KeywordJudge())
    u, t = _listen(listener, 0.0, "Main Mumbai crime branch se bol raha hoon. Aapke naam pe FIR darj hai.")
    assert u.next is None
    u, t = _listen(listener, t, "Skype pe video call pe aaiye.")
    assert u.next.step == "A4" and u.next_changed
    shown_at = u.next.made_at
    u, t = _listen(listener, t, "Kisi ko mat batana, ghar mein bhi nahi.")
    assert [p.step for p in u.came_true] == ["A4"]
    p = u.came_true[0]
    assert p.came_true and p.said_at >= shown_at and p.quote.lower().startswith("kisi ko mat batana")
    assert u.next.step == "A6" and u.next_changed


def test_a_step_said_before_the_prediction_was_shown_does_not_count():
    listener = Listener(KeywordJudge())
    _listen(listener, 0.0, "Main CBI se bol raha hoon. Aapke naam pe FIR darj hai. Skype pe video call pe aaiye.")
    p = listener.next
    assert p.step == "A4"
    p.said_at = p.made_at - 5  # found late: the caller had said it before the page showed it
    assert not p.came_true


def test_predictions_can_be_turned_off():
    listener = Listener(KeywordJudge(), predict=None)
    _listen(listener, 0.0, "Main CBI se bol raha hoon. Aapke naam pe FIR darj hai. Skype pe video call pe aaiye.")
    assert listener.next is None and listener.predictions == []
