#!/usr/bin/env python3
"""Embed subgraph definitions referenced by UUID node types in ComfyUI workflow JSON."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "workflows" / "_templates"
WORKFLOWS_DIR = REPO_ROOT / "workflows"

UUID_TYPE_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Workflows saved from another golden file reuse the same subgraph bodies under new ids.
SUBGRAPH_ID_ALIASES: dict[str, str] = {
    "9946648f-befe-4830-8f0f-0f309ad8ae5b": "e856a1af-fe5f-4934-9c1e-b17c0b25eb2f",
    "e846bb28-af4b-468e-8dc6-d53ccd1783f0": "fb515013-3f23-4eb7-aacd-3429e6821e68",
    "9eb5e812-b4d5-4e4d-add7-be79575a80d9": "fa7296b5-c974-4466-bfe3-a1f05f43b880",
}

SKIP_TEMPLATE_NAMES = {"HiRes_Fix_SDXL_reference.json"}


def load_templates() -> dict[str, dict]:
    templates: dict[str, dict] = {}
    if not TEMPLATES_DIR.is_dir():
        return templates
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        if path.name in SKIP_TEMPLATE_NAMES:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        subgraph_id = data.get("id")
        if isinstance(subgraph_id, str) and UUID_TYPE_RE.match(subgraph_id):
            templates[subgraph_id] = data
    return templates


def build_donor_index(workflows_dir: Path) -> dict[str, dict]:
    donors: dict[str, dict] = {}
    for path in sorted(workflows_dir.rglob("*.json")):
        if "_templates" in path.parts:
            continue
        try:
            workflow = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        definitions = workflow.get("definitions") or {}
        for subgraph in definitions.get("subgraphs") or []:
            if not isinstance(subgraph, dict):
                continue
            subgraph_id = subgraph.get("id")
            if isinstance(subgraph_id, str) and UUID_TYPE_RE.match(subgraph_id):
                donors[subgraph_id] = subgraph
    return donors


def referenced_subgraph_ids(workflow: dict) -> set[str]:
    refs: set[str] = set()

    def walk(obj: object) -> None:
        if isinstance(obj, dict):
            node_type = obj.get("type")
            if isinstance(node_type, str) and UUID_TYPE_RE.match(node_type):
                refs.add(node_type)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(workflow)
    return refs


def subgraph_for_id(
    subgraph_id: str,
    templates: dict[str, dict],
    donors: dict[str, dict],
) -> dict | None:
    if subgraph_id in templates:
        body = copy.deepcopy(templates[subgraph_id])
        body["id"] = subgraph_id
        return body
    if subgraph_id in donors:
        return copy.deepcopy(donors[subgraph_id])
    alias = SUBGRAPH_ID_ALIASES.get(subgraph_id)
    if alias and alias in templates:
        body = copy.deepcopy(templates[alias])
        body["id"] = subgraph_id
        return body
    return None


def embed_subgraphs(
    workflow_path: Path,
    templates: dict[str, dict],
    donors: dict[str, dict],
    dry_run: bool = False,
) -> tuple[list[str], list[str]]:
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    needed = referenced_subgraph_ids(workflow)
    if not needed:
        return [], []

    definitions = workflow.setdefault("definitions", {})
    subgraphs: list[dict] = definitions.setdefault("subgraphs", [])
    existing = {sg.get("id") for sg in subgraphs if isinstance(sg, dict)}

    added: list[str] = []
    unresolved: list[str] = []
    for subgraph_id in sorted(needed):
        if subgraph_id in existing:
            continue
        body = subgraph_for_id(subgraph_id, templates, donors)
        if body is None:
            unresolved.append(subgraph_id)
            continue
        subgraphs.append(body)
        added.append(subgraph_id)

    if added and not dry_run:
        workflow_path.write_text(
            json.dumps(workflow, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return added, unresolved


def iter_workflow_paths(workflows: list[Path] | None) -> list[Path]:
    if workflows:
        return [p if p.is_absolute() else REPO_ROOT / p for p in workflows]
    paths: list[Path] = []
    for path in sorted(WORKFLOWS_DIR.rglob("*.json")):
        if "_templates" in path.parts:
            continue
        paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "workflows",
        nargs="*",
        type=Path,
        help="Workflow JSON paths (default: all under workflows/)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true", help="Report unresolved refs only")
    args = parser.parse_args()

    templates = load_templates()
    donors = build_donor_index(WORKFLOWS_DIR)
    targets = iter_workflow_paths(args.workflows or None)

    exit_code = 0
    any_change = False
    for path in targets:
        if not path.is_file():
            print(f"[ERROR] Workflow not found: {path}", file=sys.stderr)
            return 1
        rel = path.relative_to(REPO_ROOT)
        added, unresolved = embed_subgraphs(path, templates, donors, dry_run=args.dry_run or args.check)
        if unresolved:
            exit_code = 1
            print(f"[ERROR] {rel}: unresolved subgraph id(s): {', '.join(unresolved)}")
        if added:
            any_change = True
            action = "would embed" if (args.dry_run or args.check) else "embedded"
            print(f"[OK] {rel}: {action} {len(added)} subgraph(s): {', '.join(added)}")
        elif not unresolved:
            print(f"[OK] {rel}: all referenced subgraphs present")

    if args.check and exit_code == 0 and not any_change:
        print("[OK] No missing subgraph definitions found.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
