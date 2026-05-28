#!/usr/bin/env python3
"""Sync a UUID wrapper node ports from its embedded subgraph interface.

This removes manual guessing when editing nested subgraphs in 0.4 workflow files.

Usage:
  python scripts/sync_subgraph_wrapper_ports.py workflows/flux2/klein-t2i.json --subgraph-id <uuid>
  python scripts/sync_subgraph_wrapper_ports.py <workflow.json> --subgraph-name "Generate Image" --write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_subgraph(doc: dict[str, Any], subgraph_id: str | None, subgraph_name: str | None) -> dict[str, Any]:
    defs = doc.get("definitions", {})
    subs = defs.get("subgraphs", []) if isinstance(defs, dict) else []
    cands = [s for s in subs if isinstance(s, dict)]
    if subgraph_id:
        for sg in cands:
            if sg.get("id") == subgraph_id:
                return sg
        raise ValueError(f"subgraph id not found: {subgraph_id}")
    if subgraph_name:
        matches = [sg for sg in cands if sg.get("name") == subgraph_name]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f"subgraph name not found: {subgraph_name}")
        raise ValueError(f"subgraph name is ambiguous: {subgraph_name}")
    raise ValueError("provide --subgraph-id or --subgraph-name")


def _find_wrapper_node(doc: dict[str, Any], subgraph_id: str) -> dict[str, Any]:
    for node in doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        ntype = node.get("type")
        if isinstance(ntype, str) and UUID_RE.match(ntype) and ntype == subgraph_id:
            return node
    raise ValueError(f"wrapper node for subgraph id not found in root graph: {subgraph_id}")


def _build_input_ports(sub_inputs: list[dict[str, Any]], old_inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {
        i.get("name"): i
        for i in old_inputs
        if isinstance(i, dict) and isinstance(i.get("name"), str)
    }
    out: list[dict[str, Any]] = []
    for si in sub_inputs:
        if not isinstance(si, dict):
            continue
        name = si.get("name")
        stype = si.get("type")
        old = by_name.get(name, {})
        label = si.get("label") or si.get("localized_name") or old.get("label")
        entry: dict[str, Any] = {
            "name": name if isinstance(name, str) else "",
            "type": stype if isinstance(stype, str) else "*",
            "link": old.get("link") if isinstance(old, dict) else None,
        }
        if isinstance(label, str) and label:
            entry["label"] = label
        if "widget" in old:
            entry["widget"] = old["widget"]
        out.append(entry)
    return out


def _build_output_ports(sub_outputs: list[dict[str, Any]], old_outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {
        o.get("name"): o
        for o in old_outputs
        if isinstance(o, dict) and isinstance(o.get("name"), str)
    }
    out: list[dict[str, Any]] = []
    for so in sub_outputs:
        if not isinstance(so, dict):
            continue
        name = so.get("name")
        stype = so.get("type")
        old = by_name.get(name, {})
        label = so.get("label") or so.get("localized_name") or old.get("label")
        links = old.get("links") if isinstance(old.get("links"), list) else []
        entry: dict[str, Any] = {
            "name": name if isinstance(name, str) else "",
            "type": stype if isinstance(stype, str) else "*",
            "links": links,
        }
        if isinstance(label, str) and label:
            entry["label"] = label
        out.append(entry)
    return out


def sync_wrapper_ports(doc: dict[str, Any], subgraph: dict[str, Any]) -> tuple[int, int]:
    sg_id = subgraph.get("id")
    if not isinstance(sg_id, str):
        raise ValueError("subgraph id missing")
    wrapper = _find_wrapper_node(doc, sg_id)
    old_inputs = wrapper.get("inputs") or []
    old_outputs = wrapper.get("outputs") or []
    sub_inputs = subgraph.get("inputs") or []
    sub_outputs = subgraph.get("outputs") or []

    new_inputs = _build_input_ports(sub_inputs, old_inputs)
    new_outputs = _build_output_ports(sub_outputs, old_outputs)
    wrapper["inputs"] = new_inputs
    wrapper["outputs"] = new_outputs
    return len(old_inputs), len(old_outputs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync wrapper ports from embedded subgraph interface.")
    parser.add_argument("workflow", help="Workflow JSON path")
    parser.add_argument("--subgraph-id", help="Embedded subgraph UUID id")
    parser.add_argument("--subgraph-name", help="Embedded subgraph name")
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
        subgraph = _find_subgraph(doc, args.subgraph_id, args.subgraph_name)
    except ValueError as exc:
        sys.stdout.write(f"[FAIL] {exc}\n")
        return 2

    try:
        in_count_before, out_count_before = sync_wrapper_ports(doc, subgraph)
    except ValueError as exc:
        sys.stdout.write(f"[FAIL] {exc}\n")
        return 2

    in_after = len((_find_wrapper_node(doc, subgraph["id"]).get("inputs") or []))
    out_after = len((_find_wrapper_node(doc, subgraph["id"]).get("outputs") or []))
    sys.stdout.write(
        f"[OK] wrapper {subgraph['id']} ports: inputs {in_count_before}->{in_after}, outputs {out_count_before}->{out_after}\n"
    )

    if args.write:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sys.stdout.write(f"[OK] wrote {path}\n")
    else:
        sys.stdout.write("[OK] dry-run only (use --write to persist)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
