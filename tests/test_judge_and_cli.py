import json

from teesrakaan.cli import main
from teesrakaan.judge import SPARK_SCHEMA_V1, SPARK_SYSTEM_V1, SparkJudge, SparkSized, parse_spark_reply
from teesrakaan.keywords import KeywordJudge
from teesrakaan.signals import BY_ID, SIGNALS
from teesrakaan.transcript import CALLER, Transcript

QS = [BY_ID["A1"], BY_ID["A5"]]


def test_parse_keeps_only_asked_ids_with_quotes():
    reply = '```json\n{"yes": [{"id": "A1", "quote": "main CBI se"}, {"id": "A9", "quote": "x"}, {"id": "A5", "quote": " "}]}\n```'
    answers, note = parse_spark_reply(reply, QS)
    assert [(a.id, a.quote) for a in answers] == [("A1", "main CBI se")] and note == ""


def test_parse_never_raises_on_junk():
    for junk in ("", "no", "{", '{"yes": "A1"}', "[1, 2]"):
        answers, note = parse_spark_reply(junk, QS)
        assert answers == [] and note


def test_spark_judge_sends_the_questions_and_the_dialogue():
    sent = {}

    def complete(system, user, schema):
        sent.update(system=system, user=user, schema=schema)
        return '{"yes": [{"id": "A1", "quote": "CBI se"}]}', 900, 30

    tr = Transcript()
    for i, w in enumerate("Main CBI se bol raha hoon".split()):
        tr.add(i, CALLER, w)
    reply = SparkJudge(complete).ask(QS, tr)
    assert sent["system"] == SPARK_SYSTEM_V1 and sent["schema"] == SPARK_SCHEMA_V1
    assert "CALLER: Main CBI se bol raha hoon" in sent["user"] and "A5:" in sent["user"]
    assert reply.yes[0].id == "A1" and reply.input_tokens == 900


def test_sized_judge_counts_spark_sized_tokens():
    tr = Transcript()
    tr.add(0, CALLER, "hello")
    reply = SparkSized(KeywordJudge()).ask(SIGNALS, tr)
    assert reply.input_tokens > 500 and reply.output_tokens == 16


def test_cli_simulate_and_report(example, capsys, tmp_path):
    from conftest import EXAMPLES

    main(["simulate", str(EXAMPLES / "demo-trai-marathi.json"), "--lang", "mr"])
    out = capsys.readouterr().out
    assert "RED" in out and "धोका" in out and "judge calls" in out

    target = tmp_path / "report.md"
    main(["report", str(EXAMPLES / "demo-digital-arrest.json"), "--out", str(target)])
    assert "Scam call report" in target.read_text()


def test_cli_eval_writes_results(tmp_path, capsys):
    from conftest import EXAMPLES

    labels = tmp_path / "labels.csv"
    labels.write_text(
        "call_id,set,split,is_scam,pattern,languages,t0,t_ask,ftc_class,labeller,labelled_at,notes\n"
        "demo-digital-arrest,IN-scam,dev,1,1,hi+en,1.5,56,,AG,2026-10-28T18:00,\n"
        "demo-trai-marathi,IN-scam,dev,1,3,mr,1,23.5,,AG,2026-10-28T18:00,\n"
        "demo-bank-alert-genuine,IN-genuine,dev,0,0,hi+en,,,,AG,2026-10-28T18:00,\n"
    )
    out = tmp_path / "results.json"
    main(["eval", str(EXAMPLES), "--labels", str(labels), "--out", str(out)])
    results = json.loads(out.read_text())
    assert results["by_set"]["IN-scam"]["caught_red"]["k"] == 2
    assert results["by_set"]["IN-genuine"]["false_alarms_red"]["k"] == 0
    assert results["by_set"]["IN-scam"]["warned_before_ask"]["k"] == 2
