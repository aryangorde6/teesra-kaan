from teesrakaan.keywords import KeywordJudge
from teesrakaan.signals import SIGNALS, Level, decide
from teesrakaan.transcript import CALLER, LISTENER, Transcript


def _ask(*lines):
    tr = Transcript()
    t = 0.0
    for speaker, text in lines:
        for w in text.split():
            tr.add(t, speaker, w)
            t += 0.4
    reply = KeywordJudge().ask(SIGNALS, tr)
    return {a.id: a.quote for a in reply.yes}, tr


def test_digital_arrest_lines_in_hinglish():
    yes, tr = _ask(
        (CALLER, "Main Mumbai crime branch se bol raha hoon. Aapke naam pe FIR darj hai."),
        (CALLER, "Kisi ko mat batana. Skype pe video call pe aaiye."),
        (CALLER, "Verification ke liye paise transfer kariye."),
    )
    assert {"A1", "A2", "A4", "A8", "A6"} <= yes.keys()
    assert all(tr.locate(q) is not None for q in yes.values())


def test_devanagari_hindi_lines():
    yes, _ = _ask((CALLER, "मैं सीबीआई से बोल रहा हूँ। आपके खिलाफ वारंट है। अपना ओटीपी बताइए।"))
    assert {"A1", "A2", "A5"} <= yes.keys()


def test_marathi_lines():
    yes, _ = _ask((CALLER, "तुमचा नंबर दोन तासात बंद होईल. अधिक माहितीसाठी 9 दाबा. तुमचा आधार नंबर सांगा."))
    assert {"A2", "A3", "A10", "A5"} <= yes.keys()


def test_quotes_are_whole_words_within_one_sentence():
    yes, _ = _ask((CALLER, "Pehle sun lo. Kisi ko mat batana, ghar mein bhi nahi. Theek hai?"))
    assert yes["A4"].startswith("Kisi ko mat batana")
    assert "Theek" not in yes["A4"] and "Pehle" not in yes["A4"]


def test_the_listeners_words_never_count():
    yes, _ = _ask((LISTENER, "Main police ko bata dungi, OTP nahi bataungi"), (CALLER, "Theek hai madam"))
    assert yes == {}


def test_passive_mention_of_aadhaar_is_not_an_ask():
    yes, _ = _ask((CALLER, "Aapke Aadhaar card se ek parcel bheja gaya tha."))
    assert "A5" not in yes


def test_keyword_baseline_is_fooled_by_negation():
    # A genuine bank's own advice reads like an OTP request to a keyword list.
    # This is the weakness Muse Spark's yes/no answers are meant to fix (comparison A vs C).
    yes, _ = _ask((CALLER, "Main SBI bank se bol rahi hoon. Hum kabhi OTP nahi maangte, kisi ko OTP mat bataiye."))
    assert "A5" in yes
    assert decide(yes).level == Level.RED


def test_demo_genuine_bank_alert_is_not_red(example):
    from teesrakaan.simulate import simulate

    result = simulate(example("demo-bank-alert-genuine"), KeywordJudge())
    assert result.level < Level.RED


def test_keyword_hits_for_the_paraphrase_test():
    from teesrakaan.keywords import keyword_hits

    assert {sid for sid, _ in keyword_hits("Main CBI se bol raha hoon, OTP bata do")} >= {"A1", "A5"}
    assert keyword_hits("Namaste ji, main ek sarkari daftar se baat kar raha hoon.") == []
