import json

import pytest

from rag_chunker import __version__
from rag_chunker.cli import main


def test_version_flag_prints_version_and_exits(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_main_writes_jsonl_to_stdout(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\nHello world.\n", encoding="utf-8")

    status = main([str(doc)])

    assert status == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["heading_path"] == ["Title"]
    assert record["text"] == "Title\n\nHello world."


def test_no_heading_prefix_uses_bare_body(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\nHello world.\n", encoding="utf-8")

    main([str(doc), "--no-heading-prefix"])

    record = json.loads(capsys.readouterr().out.strip())
    assert record["text"] == "Hello world."


def test_array_flag_emits_json_array(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# One\n\nFirst.\n\n# Two\n\nSecond.\n", encoding="utf-8")

    main([str(doc), "--array"])

    records = json.loads(capsys.readouterr().out)
    assert [r["heading_path"] for r in records] == [["One"], ["Two"]]


def test_stats_flag_prints_summary_to_stderr(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\nHello world.\n", encoding="utf-8")

    main([str(doc), "--stats"])

    err = capsys.readouterr().err
    assert "1 chunks" in err


def test_output_flag_writes_to_file(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\nHello world.\n", encoding="utf-8")
    out_path = tmp_path / "out.jsonl"

    main([str(doc), "-o", str(out_path)])

    record = json.loads(out_path.read_text(encoding="utf-8").strip())
    assert record["heading_path"] == ["Title"]


def test_missing_file_exits_with_error(tmp_path, capsys):
    missing = tmp_path / "missing.md"

    with pytest.raises(SystemExit) as exc_info:
        main([str(missing)])
    assert exc_info.value.code == 2
    assert "missing.md" in capsys.readouterr().err


def test_overlap_not_smaller_than_max_tokens_is_rejected(tmp_path, capsys):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n\nHello world.\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main([str(doc), "--max-tokens", "10", "--overlap", "10"])
    assert exc_info.value.code == 2
