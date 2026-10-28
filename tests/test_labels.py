import pytest

from teesrakaan.labels import COLUMNS, read_labels, sample_ftc, split_scripts, write_template


def test_split_is_forty_sixty_fixed_and_order_free():
    ids = [f"S{i:02d}" for i in range(1, 41)]
    split = split_scripts(ids)
    assert sum(v == "dev" for v in split.values()) == 16
    assert split == split_scripts(list(reversed(ids)))
    assert split != split_scripts(ids, seed=1)


def test_ftc_sample_is_by_hash_and_fixed():
    names = [f"call_{i}.wav" for i in range(1000)]
    sample = sample_ftc(names)
    assert len(sample) == 200 and sum(v == "dev" for v in sample.values()) == 50
    assert sample == sample_ftc(reversed(names))


def _sheet(tmp_path, rows):
    path = tmp_path / "labels.csv"
    write_template(path, rows)
    return path


GOOD = {
    "call_id": "IS01", "set": "IN-scam", "split": "dev", "is_scam": "1", "pattern": "1",
    "languages": "hi+en", "t0": "0:04.5", "t_ask": "61", "labeller": "AG", "labelled_at": "2026-10-29T18:00+05:30",
}


def test_a_good_sheet_reads(tmp_path):
    labels = read_labels(_sheet(tmp_path, [GOOD]))
    label = labels["IS01"]
    assert label.t0 == 4.5 and label.t_ask == 61 and label.is_scam and label.pattern == 1


@pytest.mark.parametrize("change, message", [
    ({"t0": ""}, "needs t0"),
    ({"is_scam": "0"}, "genuine call has no t0"),
    ({"t_ask": "2"}, "t_ask is before t0"),
    ({"split": "train"}, "split must be"),
    ({"labelled_at": ""}, "labelled_at is required"),
    ({"set": "FTC", "t0": "", "t_ask": ""}, "ftc_class"),
])
def test_bad_rows_are_refused(tmp_path, change, message):
    with pytest.raises(ValueError, match=message):
        read_labels(_sheet(tmp_path, [{**GOOD, **change}]))


def test_template_has_every_column(tmp_path):
    path = _sheet(tmp_path, [])
    assert path.read_text().strip() == ",".join(COLUMNS)
