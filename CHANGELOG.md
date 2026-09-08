# Changelog

## Unreleased

- `rag-chunker --version` prints the installed package version and exits.

## 0.1.0

Initial release.

- Markdown block parser (`parse_blocks`): headings, fenced code, pipe tables,
  list runs, paragraphs.
- Sentence splitter (`split_sentences`) with an abbreviation guard.
- Character-class token estimator (`estimate_tokens`, `fits_budget`).
- `chunk_markdown`: heading-scoped chunk packer with atomic code/table
  handling, sentence/line fallback splitting for oversized paragraphs and
  lists, and section-scoped trailing-prose overlap.
- `chunks_to_jsonl` for serialising chunk output.
- `rag-chunker` CLI: JSON Lines or array output, optional stats summary,
  file or stdout/stdin.
- Test suite covering parsing, sentence splitting, token estimation, and
  chunking.
