#!/usr/bin/env python3
"""Sync a UUID wrapper node ports from its embedded subgraph interface.

This removes manual guessing when editing nested subgraphs in 0.4 workflow files.

Usage:
  python scripts/sync_subgraph_wrapper_ports.py workflows/flux2/klein-t2i.json --subgraph-id <uuid>
  python scripts/sync_subgraph_wrapper_ports.py <workflow.json> --subgraph-name "Generate Image" --write
  python scripts/sync_subgraph_wrapper_ports.py <workflow.json> --subgraph-id <uuid> --wrapper-node-id 92 --write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lib.workflow_subgraph_ports import find_subgraph
from lib.workflow_subgraph_ports import find_wrapper_node
from lib.workflow_subgraph_ports import find_wrapper_node_by_id
from lib.workflow_subgraph_ports import sync_one_wrapper

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_wrapper(
    doc: dict[str, Any], subgraph: dict[str, Any], wrapper_node_id: int | None
) -> dict[str, Any]:
    if wrapper_node_id is not None:
        return find_wrapper_node_by_id(doc, wrapper_node_id)
    subgraph_id = subgraph.get("id")
    if not isinstance(subgraph_id, str):
        raise ValueError("subgraph id missing")
    return find_wrapper_node(doc, subgraph_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync wrapper ports from embedded subgraph interface.")
    parser.add_argument("workflow", help="Workflow JSON path")
    parser.add_argument("--subgraph-id", help="Embedded subgraph UUID id")
    parser.add_argument("--subgraph-name", help="Embedded subgraph name")
    parser.add_argument(
        "--wrapper-node-id",
        type=int,
        help="Root wrapper node id when multiple instances share the same subgraph type",
    )
    parser.add_argument("--write", action="store_true", help="Write changes to disk")
    args = parser.parse_args()

    path = Path(args.workflow)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        sys.stdout.write(f"[FAIL] missing workflow: {path}\n")
        return 2

    doc = _load(path)
    try:
        subgraph = find_subgraph(doc, args.subgraph_id, args.subgraph_name)
    except ValueError as exc:
        sys.stdout.write(f"[FAIL] {exc}\n")
        return 2

    try:
        wrapper = _resolve_wrapper(doc, subgraph, args.wrapper_node_id)
        in_count_before, out_count_before, links_fixed, _ = sync_one_wrapper(
            doc, subgraph, wrapper=wrapper
        )
    except ValueError as exc:
        sys.stdout.write(f"[FAIL] {exc}\n")
        return 2

    wrapper_after = _resolve_wrapper(doc, subgraph, args.wrapper_node_id)
    in_after = len((wrapper_after.get("inputs") or []))
    out_after = len((wrapper_after.get("outputs") or []))
    sys.stdout.write(
        f"[OK] wrapper {wrapper_after.get('id')} ports: inputs {in_count_before}->{in_after}, "
        f"outputs {out_count_before}->{out_after}, links realigned {links_fixed}\n"
    )

    if args.write:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sys.stdout.write(f"[OK] wrote {path}\n")
    else:
        sys.stdout.write("[OK] dry-run only (use --write to persist)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
