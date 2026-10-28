import json

import pytest

from teesrakaan.transcript import CALLER, LISTENER, Transcript, Turn, load_call, merge_speakers, normalize


def test_normalize_folds_case_punctuation_and_devanagari_digits():
    assert normalize("  OTP,  bata-do!  ") == "otp bata do"
    assert normalize("₹५०,०००  रुपये।") == "50 000 रुपये"
    assert normalize("गिरफ़्तार") == normalize("गिरफ़्तार")  # precomposed and nukta forms


def test_turn_words_are_spread_over_the_turn_or_use_given_times():
    turn = Turn(CALLER, 10.0, 14.0, "a b c d")
    assert [t for t, _ in turn.words()] == [10.0, 11.0, 12.0, 13.0]
    timed = Turn(CALLER, 10.0, 14.0, "a b", word_times=(10.5, 13.2))
    assert timed.words() == [(10.5, "a"), (13.2, "b")]


def _heard(*items):
    tr = Transcript()
    for t, speaker, text in items:
        for i, w in enumerate(text.split()):
            tr.add(t + i, speaker, w)
    return tr


def test_locate_finds_when_the_caller_said_a_quote():
    tr = _heard((0, CALLER, "Main CBI se bol raha hoon."), (10, CALLER, "Kisi ko mat batana, samjhe?"))
    assert tr.locate("main cbi se") == 0
    assert tr.locate("kisi ko mat batana") == 10
    assert tr.locate("MAT BATANA,") == 12


def test_locate_ignores_the_listeners_words_and_invented_quotes():
    tr = _heard((0, CALLER, "Aapka parcel aaya hai"), (5, LISTENER, "kya yeh scam hai OTP bata doon"))
    assert tr.locate("OTP bata doon") is None
    assert tr.locate("aapka parcel mein drugs") is None
    assert tr.locate("") is None


def test_locate_matches_whole_words_only():
    tr = _heard((0, CALLER, "cash back milega"))
    assert tr.locate("ash") is None


def test_dialogue_labels_each_side():
    tr = _heard((0, CALLER, "Hello sir"), (3, LISTENER, "Haan"), (5, CALLER, "Main bank se"))
    assert tr.dialogue() == "CALLER: Hello sir\nYOU: Haan\nCALLER: Main bank se"
    assert tr.caller_text() == "Hello sir Main bank se"
    assert tr.n_caller_words == 5


def test_load_call_checks_speakers(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"id": "x", "turns": [{"speaker": "S1", "start": 0, "end": 1, "text": "hi"}]}))
    with pytest.raises(ValueError, match="speaker"):
        load_call(path)


def test_merge_speakers_makes_every_turn_the_callers(example):
    call = merge_speakers(example("demo-digital-arrest"))
    assert {t.speaker for t in call.turns} == {CALLER}
    assert call.duration == 76.0
