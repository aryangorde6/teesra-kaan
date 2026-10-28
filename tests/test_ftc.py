import pytest

from teesrakaan.ftc import english_file_names, git_blob_sha, local_name
from teesrakaan.labels import sample_ftc


def test_english_names_are_distinct(tmp_path):
    meta = tmp_path / "metadata.csv"
    meta.write_text(
        "file_name,language,transcript,case_details,case_pdf\n"
        'audio/a_normalized.wav,en,"press 1\nnow",case-1,x.pdf\n'
        "audio/a_normalized.wav,en,press 1 now,case-2,y.pdf\n"
        "audio/b_normalized.wav,zh,...,case-3,z.pdf\n"
        "audio/c_left.wav,en,hello,case-4,w.pdf\n"
    )
    assert english_file_names(meta) == ["audio/a_normalized.wav", "audio/c_left.wav"]


def test_duplicates_count_once_in_the_sample():
    assert sample_ftc(["x.wav", "x.wav", "y.wav"], n=5, n_dev=1).keys() == {"x.wav", "y.wav"}


def test_git_blob_sha_matches_git():
    assert git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_local_names_refuse_odd_paths():
    assert local_name("audio-wav-16khz/123_normalized.wav") == "123_normalized.wav"
    for bad in ("audio/../../etc/passwd", "audio/x.wav;rm", "audio/"):
        with pytest.raises(ValueError):
            local_name(bad)
