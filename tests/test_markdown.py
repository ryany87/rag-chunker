from rag_chunker.markdown import parse_blocks


def test_empty_text_has_no_blocks():
    assert parse_blocks("") == []
    assert parse_blocks("   \n  ") == []


def test_heading_extracts_level_and_title():
    blocks = parse_blocks("##  My Heading  \n")
    assert len(blocks) == 1
    block = blocks[0]
    assert block.kind == "heading"
    assert block.level == 2
    assert block.title == "My Heading"


def test_paragraph_after_blank_lines():
    blocks = parse_blocks("# Title\n\nSome text.\n")
    assert [b.kind for b in blocks] == ["heading", "paragraph"]
    paragraph = blocks[1]
    assert paragraph.text == "Some text."
    assert paragraph.start_line == 3
    assert paragraph.end_line == 3


def test_paragraph_stops_before_next_heading():
    blocks = parse_blocks("Some text.\n# Heading\n")
    assert [b.kind for b in blocks] == ["paragraph", "heading"]
    assert blocks[0].text == "Some text."
    assert blocks[1].title == "Heading"


def test_fenced_code_block_is_atomic():
    blocks = parse_blocks("```python\ncode line\n```\n")
    assert len(blocks) == 1
    block = blocks[0]
    assert block.kind == "code"
    assert block.is_atomic is True
    assert block.start_line == 1
    assert block.end_line == 3
    assert block.text == "```python\ncode line\n```"


def test_unterminated_fence_still_becomes_one_block():
    blocks = parse_blocks("```\nabc\ndef")
    assert len(blocks) == 1
    block = blocks[0]
    assert block.kind == "code"
    assert block.start_line == 1
    assert block.end_line == 3
    assert block.text == "```\nabc\ndef"


def test_pipe_table_is_atomic():
    blocks = parse_blocks("| A | B |\n| - | - |\n| 1 | 2 |\n")
    assert len(blocks) == 1
    block = blocks[0]
    assert block.kind == "table"
    assert block.is_atomic is True
    assert block.start_line == 1
    assert block.end_line == 3


def test_bullet_list_is_not_atomic():
    blocks = parse_blocks("- item a\n- item b\n")
    assert len(blocks) == 1
    block = blocks[0]
    assert block.kind == "list"
    assert block.is_atomic is False
    assert block.start_line == 1
    assert block.end_line == 2
