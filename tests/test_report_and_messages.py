from teesrakaan.keywords import KeywordJudge
from teesrakaan.messages import COUNTRIES, FACTS, LANGS, SCRIPT_NAME, SIGNAL_NAME, script_ahead, warning
from teesrakaan.playbook import SCRIPTS, ahead
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
        assert WHAT_TO_DO["IN"][lang][0] in md


def test_every_signal_and_message_has_all_three_languages():
    assert set(SIGNAL_NAME) == {s.id for s in SIGNALS}
    for names in SIGNAL_NAME.values():
        assert set(names) == set(LANGS)
    for lang in LANGS:
        w = warning(Alarm(Level.RED, "ask", frozenset({"A1", "A5"})), {"A1": "main bank se", "A5": "OTP bataiye"}, lang)
        assert w["headline"] and w["action"] and len(w["signals"]) == 2 and w["facts"]


def test_every_country_has_its_steps_and_facts_in_every_language():
    for country in COUNTRIES:
        assert set(WHAT_TO_DO[country]) == set(LANGS)
        assert len({len(steps) for steps in WHAT_TO_DO[country].values()}) == 1
        assert any(where == country for _, where, _ in FACTS)
    for _, where, text in FACTS:
        assert where in COUNTRIES and set(text) == set(LANGS) and all(v.strip() for v in text.values())


def test_in_the_us_a_red_warning_sends_you_to_the_ftc_not_1930():
    alarm = Alarm(Level.RED, "ask", frozenset({"A1", "A2", "A6"}))
    quotes = {"A1": "this is the Social Security Administration", "A2": "a warrant for your arrest", "A6": "gift cards"}
    us, india = warning(alarm, quotes, "en", "US"), warning(alarm, quotes, "en")
    assert "ReportFraud.ftc.gov" in us["action"] and "1930" not in us["action"]
    assert "1930" in india["action"]
    assert any("gift cards" in f for f in us["facts"]) and not any("digital arrest" in f for f in us["facts"])
    # Amber advice names no helpline, so it's the same everywhere.
    amber = Alarm(Level.AMBER, "pressure", frozenset({"A2", "A3"}))
    assert warning(amber, {}, "hi", "US")["action"] == warning(amber, {}, "hi")["action"]


def test_the_us_report_pack_names_the_ftc(example):
    call = example("demo-digital-arrest")
    result = simulate(call, KeywordJudge())
    md = build_report(call, result.listener, "en", country="US").to_markdown()
    assert "ReportFraud.ftc.gov" in md and "IdentityTheft.gov" in md
    assert "1930" not in md and "cybercrime.gov.in" not in md
    assert "digital arrest" not in md  # an Indian fact line


def test_no_warning_when_nothing_is_wrong():
    assert warning(Alarm(Level.NONE, "", frozenset({"A1"})), {}, "en") is None


def test_the_family_message_quotes_dont_tell_anyone_first():
    alarm = Alarm(Level.RED, "ask", frozenset({"A1", "A4", "A6"}))
    quotes = {"A1": "main CBI se", "A4": "kisi ko mat batana", "A6": "paise transfer kijiye"}
    for lang in LANGS:
        msg = warning(alarm, quotes, lang)["family"]
        assert msg.startswith("Teesra Kaan:") and "“kisi ko mat batana”" in msg
    assert "“" not in warning(alarm, {}, "en")["family"]


def test_every_script_has_a_name_and_its_rest_reads_in_every_language():
    assert set(SCRIPT_NAME) == {s.id for s in SCRIPTS}
    for names in SCRIPT_NAME.values():
        assert set(names) == set(LANGS) and all(v.strip() for v in names.values())
    for lang in LANGS:
        known = script_ahead(ahead({"A1", "A2", "A8"}), lang)
        assert SCRIPT_NAME["digital-arrest"][lang] in known["matches"] and len(known["steps"]) == 2 and not known["note"]
        unsure = script_ahead(ahead({"A1", "A2"}), lang)
        assert not unsure["steps"] and unsure["note"] and SCRIPT_NAME["kyc"][lang] in unsure["matches"]
        assert script_ahead(None, lang)["note"] and not script_ahead(None, lang)["matches"]
        assert script_ahead(ahead({"A1", "A2", "A8", "A4", "A6"}), lang)["note"] != unsure["note"]


def test_every_warning_the_page_can_show_has_a_line_to_record():
    from teesrakaan.messages import COUNTRIES, LANGS, voice_id, voice_lines

    lines = voice_lines()
    assert len(lines) == 9
    for level in ("red", "amber"):
        for lang in LANGS:
            for country in COUNTRIES:
                line = lines[voice_id(level, lang, country)]
                assert line["level"] == level and line["language"] == lang
                assert all(line["lines"])
    assert list(lines)[:6] == ["W-red-IN-en", "W-red-IN-hi", "W-red-IN-mr", "W-amber-en", "W-amber-hi", "W-amber-mr"]
