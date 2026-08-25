"""Heading-aware chunk assembly.

The parser hands back a flat list of blocks; this module turns that into chunks
that respect the rules laid out in the README: a chunk never spans a heading,
code and tables are never split, long paragraphs fall back to sentence
boundaries, and overlap carries trailing prose forward within a section only
(it resets at every heading, since a sentence from "Rollback" has no business
opening a chunk in "Checks").

The packing itself works over a list of independently-sized "pieces" per
section (whole blocks, or their sentence/line breakdown when a block alone
does not fit the budget) rather than over blocks directly, so a code block
that fits can still share a chunk with the paragraph in front of it, and a
paragraph that does not fit gets split without disturbing its neighbours.
"""

import json

from .markdown import parse_blocks
from .sentences import split_sentences
from .tokens import estimate_tokens

__all__ = [
    "Chunk",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_OVERLAP",
    "chunk_markdown",
    "chunks_to_jsonl",
]

DEFAULT_MAX_TOKENS = 512
DEFAULT_OVERLAP = 64


def _heading_prefix(heading_path):
    return " > ".join(heading_path)


class Chunk(object):
    """One emittable unit: a heading path plus the body text under it."""

    __slots__ = (
        "index",
        "body",
        "heading_path",
        "start_line",
        "end_line",
        "oversized",
        "text",
        "token_estimate",
    )

    def __init__(self, index, body, heading_path, start_line, end_line, oversized=False):
        self.index = index
        self.body = body
        self.heading_path = list(heading_path)
        self.start_line = start_line
        self.end_line = end_line
        self.oversized = oversized
        prefix = _heading_prefix(self.heading_path)
        self.text = "%s\n\n%s" % (prefix, body) if prefix else body
        self.token_estimate = estimate_tokens(self.text)

    def to_dict(self):
        return {
            "index": self.index,
            "text": self.text,
            "heading_path": list(self.heading_path),
            "start_line": self.start_line,
            "end_line": self.end_line,
            "token_estimate": self.token_estimate,
        }

    def __repr__(self):
        return "Chunk(index=%d, lines=%d-%d, tokens=%d, oversized=%s)" % (
            self.index,
            self.start_line,
            self.end_line,
            self.token_estimate,
            self.oversized,
        )


def _sentence_spans(block):
    """Break a paragraph block into (sentence, start_line, end_line) spans."""
    text = block.text
    spans = []
    cursor = 0
    for sentence in split_sentences(text):
        idx = text.index(sentence, cursor)
        end_idx = idx + len(sentence)
        start_line = block.start_line + text.count("\n", 0, idx)
        end_line = block.start_line + text.count("\n", 0, end_idx)
        spans.append((sentence, start_line, end_line))
        cursor = end_idx
    return spans


def _line_spans(block):
    """Break a list block into (line, line_no, line_no) spans."""
    spans = []
    line_no = block.start_line
    for line in block.text.split("\n"):
        if line.strip():
            spans.append((line, line_no, line_no))
        line_no += 1
    return spans


def _pieces_for_block(block, heading_path, max_tokens):
    """Return the block as one piece, or split it if it cannot stand alone.

    Code and tables are atomic and are always returned whole, even when that
    means the piece will end up oversized -- there is no safe way to cut one
    in half. Paragraphs and lists split into sentences or lines, but only
    when the whole block does not already fit, so short blocks stay intact.
    """
    prefix = _heading_prefix(heading_path)

    def fits(body):
        text = "%s\n\n%s" % (prefix, body) if prefix else body
        return estimate_tokens(text) <= max_tokens

    if block.is_atomic or fits(block.text):
        return [(block.text, block.start_line, block.end_line)]

    if block.kind == "paragraph":
        spans = _sentence_spans(block)
    else:
        spans = _line_spans(block)

    return spans if spans else [(block.text, block.start_line, block.end_line)]


def _trailing_overlap(body, overlap_tokens):
    """Pull the last ``overlap_tokens`` worth of sentences off ``body``."""
    if overlap_tokens <= 0:
        return ""
    sentences = split_sentences(body)
    if not sentences:
        return ""
    picked = []
    total = 0
    for sentence in reversed(sentences):
        picked.append(sentence)
        total += estimate_tokens(sentence)
        if total >= overlap_tokens:
            break
    picked.reverse()
    return " ".join(picked)


def _pack_section(heading_path, pieces, max_tokens, overlap):
    """Pack a section's pieces into chunk bodies, respecting the budget."""
    prefix = _heading_prefix(heading_path)

    def fits(body):
        text = "%s\n\n%s" % (prefix, body) if prefix else body
        return estimate_tokens(text) <= max_tokens

    results = []
    acc_parts = []
    acc_start = None
    acc_end = None
    overlap_text = ""

    def acc_body():
        parts = ([overlap_text] if overlap_text else []) + acc_parts
        return "\n\n".join(parts)

    def flush():
        body = acc_body()
        if body.strip():
            results.append((body, acc_start, acc_end, False))
            return _trailing_overlap(body, overlap) if overlap > 0 else ""
        return ""

    for text, start, end in pieces:
        if not fits(text):
            overlap_text = flush()
            acc_parts = []
            acc_start = acc_end = None
            results.append((text, start, end, True))
            overlap_text = ""
            continue

        candidate_body = "\n\n".join((([overlap_text] if overlap_text else [])) + acc_parts + [text])
        if fits(candidate_body):
            acc_parts.append(text)
            acc_start = start if acc_start is None else min(acc_start, start)
            acc_end = end if acc_end is None else max(acc_end, end)
            continue

        overlap_text = flush()
        acc_parts = [text]
        acc_start, acc_end = start, end
        fresh_body = "\n\n".join((([overlap_text] if overlap_text else [])) + acc_parts)
        if not fits(fresh_body):
            overlap_text = ""

    flush()
    return results


def chunk_markdown(text, max_tokens=DEFAULT_MAX_TOKENS, overlap=DEFAULT_OVERLAP):
    """Split markdown ``text`` into :class:`Chunk` objects."""
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap < 0:
        raise ValueError("overlap must not be negative")
    if overlap >= max_tokens:
        raise ValueError("overlap must be smaller than max_tokens")

    chunks = []
    heading_stack = []
    section_blocks = []

    def flush_section():
        if not section_blocks:
            return
        path = [title for _level, title in heading_stack]
        pieces = []
        for block in section_blocks:
            pieces.extend(_pieces_for_block(block, path, max_tokens))
        for body, start, end, oversized in _pack_section(path, pieces, max_tokens, overlap):
            chunks.append(Chunk(len(chunks), body, path, start, end, oversized))
        del section_blocks[:]

    for block in parse_blocks(text):
        if block.kind == "heading":
            flush_section()
            while heading_stack and heading_stack[-1][0] >= block.level:
                heading_stack.pop()
            heading_stack.append((block.level, block.title))
        else:
            section_blocks.append(block)
    flush_section()

    return chunks


def chunks_to_jsonl(chunks):
    """Serialise ``chunks`` to a JSON-lines string, one record per chunk."""
    return "\n".join(json.dumps(chunk.to_dict(), ensure_ascii=False) for chunk in chunks)
