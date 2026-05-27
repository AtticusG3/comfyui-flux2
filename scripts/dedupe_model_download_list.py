#!/usr/bin/env python3
"""Collapse duplicate aria2 model download blocks that share dir= and out=."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def iter_blocks(text: str):
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("https://") or line.startswith("http://"):
            if current:
                block = "\n".join(current).strip()
                if block:
                    yield block
            current = [line]
            continue
        if current and (line.startswith("  ") or line.startswith("\t") or line == ""):
            current.append(line)
            continue
        if current:
            block = "\n".join(current).strip()
            if block:
                yield block
            current = []
    if current:
        block = "\n".join(current).strip()
        if block:
            yield block


def block_key(block: str) -> tuple[str, str] | None:
    out_match = re.search(r"^\s*out=(.+)$", block, re.MULTILINE)
    if not out_match:
        return None
    dir_match = re.search(r"^\s*dir=(.+)$", block, re.MULTILINE)
    dir_name = dir_match.group(1).strip() if dir_match else ""
    return dir_name, out_match.group(1).strip()


def block_url(block: str) -> str:
    for line in block.splitlines():
        if line.startswith("https://") or line.startswith("http://"):
            return line.strip()
    return ""


def dedupe_list_path(list_path: Path) -> int:
    if not list_path.is_file():
        return 0

    text = list_path.read_text(encoding="utf-8")
    if not text.strip():
        return 0

    seen_urls: dict[tuple[str, str], str] = {}
    kept: list[str] = []
    removed = 0

    for block in iter_blocks(text):
        key = block_key(block)
        if key is None:
            kept.append(block)
            continue
        url = block_url(block)
        prior = seen_urls.get(key)
        if prior is not None:
            removed += 1
            if prior != url:
                dir_name, out_name = key
                print(
                    f"[WARN] Duplicate model download {dir_name}/{out_name} "
                    f"with different URL; keeping first entry.",
                    file=sys.stderr,
                )
            continue
        seen_urls[key] = url
        kept.append(block)

    if removed:
        list_path.write_text(
            "\n\n".join(kept) + ("\n" if kept else ""),
            encoding="utf-8",
        )
        print(f"[INFO] Deduped model download list: removed {removed} duplicate block(s).")

    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "list_path",
        type=Path,
        help="aria2 input file (models-*.txt format, updated in place)",
    )
    args = parser.parse_args()
    dedupe_list_path(args.list_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
