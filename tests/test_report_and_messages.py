from teesrakaan.keywords import KeywordJudge
from teesrakaan.messages import LANGS, SIGNAL_NAME, warning
from teesrakaan.report import WHAT_TO_DO, build_report, extract
from teesrakaan.signals import SIGNALS, Alarm, Level
from teesrakaan.simulate import simulate


def test_extract_finds_what_the_complaint_form_asks_for():
    found = extract(
        "Do lakh rupaye bhejiye. ₹50,000 abhi. Account 501234567890, UPI rbi.verify@okaxis, "
        "call 98765 43210 or +91-9123456789, mail help@fake-rbi.in, AnyDesk download karo, open www.fake-kyc.com"
    )
    assert "₹50,000" in found["amounts"] and "lakh rupaye" not in found["amounts"]
    assert found["upi_ids"] == ["rbi.verify@okaxis"]
    assert found["emails"] == ["help@fake-rbi.in"]
    assert found["account_numbers"] == ["501234567890"]
    assert found["phone_numbers"] == ["98765 43210", "+91-9123456789"]
    assert found["apps"] == ["anydesk"]
    assert "www.fake-kyc.com" in found["links"]


def test_extract_reads_devanagari_digits():
    assert extract("५०,००० रुपये भेजिए")["amounts"] == ["50,000 रुपये"]


def test_report_pack_for_the_demo_call(example):
    call = example("demo-digital-arrest")
    result = simulate(call, KeywordJudge())
    pack = build_report(call, result.listener)
    assert pack.level == "red" and pack.warned_at == result.t_warn
    assert [c["said_at"] for c in pack.claims] == sorted(c["said_at"] for c in pack.claims)
    assert "rbi.verify@okaxis" in pack.mentioned["upi_ids"]
    assert "501234567890" in pack.mentioned["account_numbers"]
    md = pack.to_markdown()
    assert "1930" in md and "cybercrime.gov.in" in md and "sancharsaathi.gov.in" in md
    assert "Inspector Sharma" in md
    assert "digital arrest" in md  # the fact line for A1 + A8


def test_report_pack_in_hindi_and_marathi(example):
    call = example("demo-trai-marathi")
    result = simulate(call, KeywordJudge())
    for lang in ("hi", "mr"):
        md = build_report(call, result.listener, lang).to_markdown()
        assert WHAT_TO_DO[lang][0] in md


def test_every_signal_and_message_has_all_three_languages():
    assert set(SIGNAL_NAME) == {s.id for s in SIGNALS}
    for names in SIGNAL_NAME.values():
        assert set(names) == set(LANGS)
    for lang in LANGS:
        w = warning(Alarm(Level.RED, "ask", frozenset({"A1", "A5"})), {"A1": "main bank se", "A5": "OTP bataiye"}, lang)
        assert w["headline"] and w["action"] and len(w["signals"]) == 2 and w["facts"]


def test_no_warning_when_nothing_is_wrong():
    assert warning(Alarm(Level.NONE, "", frozenset({"A1"})), {}, "en") is None
