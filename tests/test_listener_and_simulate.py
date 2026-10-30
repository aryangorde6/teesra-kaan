from dataclasses import dataclass, field

from teesrakaan.judge import Answer, Reply
from teesrakaan.keywords import KeywordJudge
from teesrakaan.listener import Listener
from teesrakaan.signals import Level
from teesrakaan.simulate import Timing, check_points, simulate
from teesrakaan.transcript import CALLER, LISTENER, Call, Turn


@dataclass
class ScriptedJudge:
    """Says "yes" to a signal, with a fixed quote, once that quote has been heard from anyone."""

    script: dict[str, str]
    name: str = "scripted"
    asked: list[tuple[str, ...]] = field(default_factory=list)

    def ask(self, questions, transcript):
        self.asked.append(tuple(q.id for q in questions))
        heard = " ".join(line.text for line in transcript.lines).lower()
        return Reply([Answer(q.id, self.script[q.id]) for q in questions
                      if q.id in self.script and self.script[q.id].lower() in heard])


def _call(*turns):
    return Call("t", tuple(Turn(*t) for t in turns))


def test_invented_quotes_are_rejected_and_raise_nothing():
    listener = Listener(ScriptedJudge({"A1": "main CBI se", "A5": "OTP bataiye"}))
    for i, w in enumerate("Hello madam aapka courier aaya hai".split()):
        listener.hear(i, CALLER, w)
    for i, w in enumerate("main CBI se OTP bataiye".split()):  # only the listener says these words
        listener.hear(10 + i, LISTENER, w)
    listener.judge = ScriptedJudge({"A1": "main CBI se", "A5": "OTP bataiye"})
    update = listener.check(20, latency=1)
    assert update.alarm.level == Level.NONE
    assert {sid for sid, _ in listener.rejected} == {"A1", "A5"}


def test_found_signals_stick_and_are_not_asked_again():
    judge = ScriptedJudge({"A1": "crime branch se", "A2": "FIR darj"})
    listener = Listener(judge)
    for i, w in enumerate("Main crime branch se bol raha hoon".split()):
        listener.hear(i, CALLER, w)
    listener.check(7, latency=1)
    for i, w in enumerate("Aapke naam pe FIR darj hai".split()):
        listener.hear(10 + i, CALLER, w)
    listener.check(17, latency=1)
    assert "A1" in judge.asked[0] and "A1" not in judge.asked[1]
    assert listener.found["A1"].said_at == 1 and listener.found["A1"].found_at == 8
    assert listener.alarm.level == Level.AMBER


def test_no_new_caller_words_means_no_judge_call():
    judge = ScriptedJudge({})
    listener = Listener(judge)
    listener.hear(0, CALLER, "Hello")
    assert listener.check(1, latency=0) is not None
    listener.hear(2, LISTENER, "Haan")
    assert listener.check(3, latency=0) is None
    assert len(judge.asked) == 1


def test_check_points_cover_long_turns_and_turn_ends():
    call = _call((CALLER, 0, 14, "x " * 30), (LISTENER, 15, 16, "haan"), (CALLER, 17, 20, "y z"))
    points = check_points(call, Timing(transcribe_delay=1, check_every=6))
    assert points == [(7, False), (13, False), (15, True), (21, True)]


def test_warning_time_includes_transcription_and_judge_delay():
    call = _call((CALLER, 0, 4, "Main CBI se hoon"), (CALLER, 5, 8, "FIR darj hai"))
    judge = ScriptedJudge({"A1": "CBI se", "A2": "FIR darj"})
    result = simulate(call, judge, Timing(transcribe_delay=1, judge_latency=2, check_every=10))
    # turn 1 ends at 4, is in the transcript at 5, answered at 7; turn 2 at 8 + 1 + 2 = 11
    assert result.listener.found["A1"].found_at == 7
    assert result.t_warn == 11 and result.t_red is None


def test_a_busy_judge_delays_the_next_check():
    call = _call((CALLER, 0, 2, "Main CBI se"), (CALLER, 2.5, 3, "FIR darj"))
    judge = ScriptedJudge({"A1": "CBI se", "A2": "FIR darj"})
    result = simulate(call, judge, Timing(transcribe_delay=0, judge_latency=5, check_every=10))
    # the second check was due at 3 but waits for the judge, free at 2 + 5 = 7
    assert result.t_warn == 12
    assert result.listener.judge_calls == 2


def test_demo_digital_arrest_warns_before_the_ask(example):
    call = example("demo-digital-arrest")
    result = simulate(call, KeywordJudge())
    label = call.label
    assert result.level == Level.RED
    assert result.t_warn < result.t_red < label["t_ask"]
    red = next(u for u in result.listener.updates if u.alarm.level == Level.RED)
    assert red.alarm.rule == "digital-arrest opening"


def test_demo_marathi_call_goes_red_on_the_aadhaar_and_otp_ask(example):
    result = simulate(example("demo-trai-marathi"), KeywordJudge())
    assert result.level == Level.RED
    assert {"A1", "A2", "A10", "A5"} <= result.listener.found.keys()


def test_stop_at_red_saves_judge_calls(example):
    call = example("demo-digital-arrest")
    full = simulate(call, KeywordJudge())
    early = simulate(call, KeywordJudge(), stop_at_red=True)
    assert early.t_red == full.t_red
    assert early.listener.judge_calls < full.listener.judge_calls
    assert early.listener.transcript.n_words == full.listener.transcript.n_words  # the report still gets every word



def test_the_checked_judge_asks_its_overall_view_once_and_keeps_it_apart():
    from teesrakaan.judge import CheckedJudge, Completion, FreeFormJudge, SparkJudge
    from teesrakaan.listener import Listener
    from teesrakaan.signals import SCAM

    asked = []

    def complete(system, user, schema):
        asked.append("verdict" if "scam" in schema["properties"] else "signs")
        if asked[-1] == "verdict":
            return Completion('{"scam": true}', 100, 5, 0.4)
        return Completion('{"yes": [{"id": "A1", "quote": "main bank se"}]}', 900, 30, 1.2)

    listener = Listener(CheckedJudge(SparkJudge(complete), FreeFormJudge(complete)))
    for i, w in enumerate("main bank se bol raha hoon".split()):
        listener.hear(i * 0.4, "caller", w)
    update = listener.check(3.0)
    assert sorted(asked) == ["signs", "verdict"] and update.t == 3.0 + 1.2  # in parallel: the slower one
    assert listener.alarm.level == Level.AMBER and set(listener.found) == {"A1"} and listener.overall_at == 4.2
    listener.hear(3.0, "caller", "ji")
    listener.check(5.0)
    assert asked.count("verdict") == 1 and SCAM.id not in listener.found


def test_the_keyword_baseline_keeps_the_two_signal_rules():
    from teesrakaan.listener import Listener
    from teesrakaan.signals import SIGNALS, decide

    listener = Listener(KeywordJudge())
    assert listener.signals == SIGNALS and listener.decide is decide
