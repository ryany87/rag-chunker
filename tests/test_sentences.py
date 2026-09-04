from rag_chunker.sentences import ABBREVIATIONS, split_sentences


def test_empty_text_has_no_sentences():
    assert split_sentences("") == []


def test_splits_on_terminal_punctuation():
    text = "Hello world. This is a test."
    assert split_sentences(text) == ["Hello world.", "This is a test."]


def test_abbreviation_does_not_split():
    assert "dr" in ABBREVIATIONS
    text = "Dr. Chen arrived."
    assert split_sentences(text) == ["Dr. Chen arrived."]


def test_middle_initial_does_not_split():
    text = "J. Smith wrote the report."
    assert split_sentences(text) == ["J. Smith wrote the report."]


def test_numbered_list_marker_does_not_split():
    text = "3. Three is a good number."
    assert split_sentences(text) == ["3. Three is a good number."]


def test_decimal_number_does_not_split():
    text = "Version 3.5 is out. See below."
    assert split_sentences(text) == ["Version 3.5 is out.", "See below."]
