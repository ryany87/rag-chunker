"""Command-line entry point: read markdown, write chunk records as JSON."""

import argparse
import json
import sys

from . import __version__
from .chunker import DEFAULT_MAX_TOKENS, DEFAULT_OVERLAP, chunk_markdown

__all__ = ["main", "build_parser"]


def _read_input(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _record(chunk, heading_prefix):
    record = chunk.to_dict()
    if not heading_prefix:
        # to_dict()'s "text" always carries the prefix chunk.text was built
        # with; swap in the bare body rather than re-deriving it.
        record["text"] = chunk.body
    return record


def _print_stats(chunks, stream):
    if not chunks:
        print("0 chunks", file=stream)
        return
    tokens = [chunk.token_estimate for chunk in chunks]
    oversized = sum(1 for chunk in chunks if chunk.oversized)
    print(
        "%d chunks | tokens min %d avg %d max %d | %d oversized"
        % (
            len(chunks),
            min(tokens),
            round(sum(tokens) / len(tokens)),
            max(tokens),
            oversized,
        ),
        file=stream,
    )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="rag-chunker",
        description="Split a markdown document into retrieval-ready chunks.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s " + __version__,
    )
    parser.add_argument("path", help="markdown file to chunk, or - for stdin")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="chunk size ceiling, heading prefix included (default: %(default)s)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        help="trailing tokens repeated in the next chunk of a section (default: %(default)s)",
    )
    parser.add_argument(
        "--no-heading-prefix",
        action="store_true",
        help="do not prepend the heading path to the chunk text",
    )
    parser.add_argument(
        "--array",
        action="store_true",
        help="emit one indented JSON array instead of JSON lines",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="print a size summary to stderr",
    )
    parser.add_argument(
        "-o",
        dest="output",
        metavar="PATH",
        help="write the result to a file instead of stdout",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = _read_input(args.path)
    except OSError as exc:
        parser.error("%s: %s" % (args.path, exc.strerror or exc))

    try:
        chunks = chunk_markdown(text, max_tokens=args.max_tokens, overlap=args.overlap)
    except ValueError as exc:
        parser.error(str(exc))

    records = [_record(chunk, not args.no_heading_prefix) for chunk in chunks]
    if args.array:
        payload = json.dumps(records, ensure_ascii=False, indent=2)
    else:
        payload = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
    else:
        print(payload)

    if args.stats:
        _print_stats(chunks, sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
