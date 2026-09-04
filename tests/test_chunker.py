import json

import pytest

from rag_chunker.chunker import chunk_markdown, chunks_to_jsonl
from rag_chunker.sentences import split_sentences

NUMBER_SENTENCES = (
    "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten."
)
NUMBER_WORDS = [
    "One", "Two", "Three", "Four", "Five",
    "Six", "Seven", "Eight", "Nine", "Ten",
]


def test_empty_text_has_no_chunks():
    assert chunk_markdown("") == []


def test_single_section_becomes_one_chunk():
    chunks = chunk_markdown("# Title\n\nHello world.\n")
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.heading_path == ["Title"]
    assert chunk.body == "Hello world."
    assert chunk.oversized is False
    assert chunk.start_line == 3
    assert chunk.end_line == 3
    assert chunk.text == "Title\n\nHello world."


def test_chunks_never_span_a_heading():
    text = "# One\n\nFirst para.\n\n# Two\n\nSecond para.\n"
    chunks = chunk_markdown(text)
    assert [c.heading_path for c in chunks] == [["One"], ["Two"]]
    assert [c.body for c in chunks] == ["First para.", "Second para."]
    assert [c.index for c in chunks] == [0, 1]


def test_no_heading_means_no_prefix():
    chunks = chunk_markdown("Just a paragraph with no heading.\n")
    assert len(chunks) == 1
    assert chunks[0].heading_path == []
    assert chunks[0].text == chunks[0].body


def test_code_block_stays_whole_even_when_oversized():
    code = " ".join(["x"] * 100)
    text = "# Big\n\n```\n" + code + "\n```\n"
    chunks = chunk_markdown(text, max_tokens=10, overlap=0)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.oversized is True
    assert chunk.heading_path == ["Big"]
    assert chunk.body.startswith("```")
    assert chunk.body.endswith("```")
    assert chunk.body.count("x") == 100
    assert chunk.start_line == 3
    assert chunk.end_line == 5


def test_long_paragraph_falls_back_to_sentence_splits():
    text = "# Numbers\n\n" + NUMBER_SENTENCES + "\n"
    chunks = chunk_markdown(text, max_tokens=8, overlap=0)
    assert len(chunks) > 1
    assert all(not c.oversized for c in chunks)
    assert all(c.token_estimate <= 8 for c in chunks)

    combined = " ".join(c.body for c in chunks)
    positions = [combined.index(word) for word in NUMBER_WORDS]
    assert positions == sorted(positions)
    for word in NUMBER_WORDS:
        assert combined.count(word) == 1


def test_overlap_carries_a_sentence_into_the_next_chunk():
    text = "# Numbers\n\n" + NUMBER_SENTENCES + "\n"
    chunks = chunk_markdown(text, max_tokens=8, overlap=3)
    assert len(chunks) > 1
    assert all(not c.oversized for c in chunks)

    for first, second in zip(chunks, chunks[1:]):
        first_sentences = split_sentences(first.body)
        second_first_sentence = split_sentences(second.body)[0]
        assert second_first_sentence in first_sentences


def test_max_tokens_must_be_positive():
    with pytest.raises(ValueError):
        chunk_markdown("text", max_tokens=0)


def test_overlap_must_not_be_negative():
    with pytest.raises(ValueError):
        chunk_markdown("text", overlap=-1)


def test_overlap_must_be_smaller_than_max_tokens():
    with pytest.raises(ValueError):
        chunk_markdown("text", max_tokens=10, overlap=10)


def test_chunks_to_jsonl_round_trips():
    chunks = chunk_markdown("# Title\n\nHello world.\n")
    lines = chunks_to_jsonl(chunks).split("\n")
    assert len(lines) == len(chunks)
    for line, chunk in zip(lines, chunks):
        assert json.loads(line) == chunk.to_dict()
