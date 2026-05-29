#!/usr/bin/env python3
"""Validate ComfyUI workflow JSON (0.4 / 1.0) and optional pack audit."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lib.workflow_validate_cli import emit
from lib.workflow_validate_cli import expand_paths
from lib.workflow_validate_cli import run_validator_script
from lib.workflow_validate_cli import to_rel_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_04 = REPO_ROOT / "schemas/comfy/workflow-definition-v0.4.json"
SCHEMA_10 = REPO_ROOT / "schemas/comfy/workflow-definition-v1.0.json"
AUDIT_SCRIPT = REPO_ROOT / "scripts/audit_workflow_assets.py"
SEMANTICS_SCRIPT = REPO_ROOT / "scripts/validate_workflow_semantics.py"
TOPOLOGY_SCRIPT = REPO_ROOT / "scripts/validate_workflow_topology.py"
FORMAT_04, FORMAT_10, FORMAT_API = "0.4", "1.0", "API"
TAG_04, TAG_10 = "schema-ComfyWorkflow0_4", "schema-ComfyWorkflow1_0"

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def looks_like_api(data):
    return isinstance(data, dict) and data and all(
        isinstance(v, dict) and "class_type" in v and "inputs" in v for v in data.values()
    )

def looks_like_ui_graph(data):
    return isinstance(data, dict) and isinstance(data.get("nodes"), list) and isinstance(data.get("links"), list)

def detect_format(data):
    if looks_like_api(data) and not looks_like_ui_graph(data):
        return FORMAT_API, ""
    if not looks_like_ui_graph(data):
        return None, "content is neither UI graph nor API prompt map"
    version = data.get("version")
    has_state = isinstance(data.get("state"), dict)
    has_legacy = isinstance(data.get("last_node_id"), (int, float, str)) and isinstance(data.get("last_link_id"), (int, float))
    if version in (1, 1.0):
        if has_state:
            return FORMAT_10, ""
        return None, "version 1 without state"
    if version == 0.4 and has_legacy:
        return FORMAT_04, ""
    if has_legacy and not has_state:
        return FORMAT_04, f"litegraph 0.4 (version={version!r})"
    if has_state:
        return FORMAT_10, "state without version; treating as 1.0"
    return None, f"cannot resolve format (version={version!r})"

def check_schema(data, fmt):
    try:
        import jsonschema
    except ImportError:
        return False, "jsonschema not installed (pip install jsonschema==4.26.0)"
    path, tag = (SCHEMA_04, TAG_04) if fmt == FORMAT_04 else (SCHEMA_10, TAG_10)
    if not path.is_file():
        return False, f"{tag}: schema missing: {path}"
    validator = jsonschema.Draft7Validator(load_json(path))
    errors = list(validator.iter_errors(data))
    if not errors:
        return True, f"{tag} ({len(data.get('nodes') or [])} nodes)"
    err = errors[0]
    loc = "/".join(str(p) for p in err.absolute_path)
    extra = f" (+{len(errors)-1} more)" if len(errors) > 1 else ""
    return False, f"{tag}: {loc}: {err.message}{extra}"

def node_ids(data):
    return {n.get("id") for n in (data.get("nodes") or []) if isinstance(n, dict) and "id" in n}

def check_links(data):
    nodes = node_ids(data)
    links = data.get("links")
    if not isinstance(links, list):
        return False, "links: expected array"
    if not links:
        return True, "0 links"
    first = links[0]
    failures = 0
    if isinstance(first, list):
        for link in links:
            if not isinstance(link, list) or len(link) < 5:
                failures += 1
                continue
            if link[1] not in nodes or link[3] not in nodes:
                failures += 1
        kind = "tuple"
    elif isinstance(first, dict):
        for link in links:
            if not isinstance(link, dict):
                failures += 1
                continue
            if link.get("origin_id") not in nodes or link.get("target_id") not in nodes:
                failures += 1
        kind = "object"
    else:
        return False, "links[0] is neither tuple nor object"
    if failures:
        return False, f"{failures} dangling or malformed {kind} link(s)"
    return True, f"{len(links)} {kind} links, {len(nodes)} nodes"

def check_api_links(data):
    if not isinstance(data, dict):
        return False, "prompt: top-level must be object"
    ids = set(data.keys())
    failures = sum(
        1
        for node in data.values()
        if isinstance(node, dict)
        for v in (node.get("inputs") or {}).values()
        if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0] not in ids
    )
    if failures:
        return False, f"{failures} dangling API input reference(s)"
    return True, f"{len(ids)} API nodes"

def validate_file(path: Path) -> bool:
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        rel = path
    if not path.is_file():
        emit(rel, "parse", False, "file missing")
        return False
    try:
        data = load_json(path)
    except json.JSONDecodeError as exc:
        emit(rel, "parse", False, str(exc))
        return False
    emit(rel, "parse", True)
    fmt, note = detect_format(data)
    if fmt is None:
        emit(rel, "format", False, note)
        return False
    if fmt == FORMAT_API:
        emit(rel, "format", True, "API/prompt")
        ok_links, msg = check_api_links(data)
        emit(rel, "links", ok_links, msg)
        emit(rel, "schema", True, "skipped; use comfy-router for prompt-format-DRAFT")
        return ok_links
    emit(rel, "format", True, note or fmt)
    ok_schema, schema_msg = check_schema(data, fmt)
    emit(rel, "schema", ok_schema, schema_msg)
    ok_links, links_msg = check_links(data)
    emit(rel, "links", ok_links, links_msg)
    return ok_schema and ok_links



def run_topology(paths):
    return run_validator_script(
        script_path=TOPOLOGY_SCRIPT,
        repo_root=REPO_ROOT,
        rel_paths=to_rel_paths(paths, REPO_ROOT),
        gate_label="topology",
        extra_args=["--check-wrapper"],
    )

def run_semantics(paths):
    return run_validator_script(
        script_path=SEMANTICS_SCRIPT,
        repo_root=REPO_ROOT,
        rel_paths=to_rel_paths(paths, REPO_ROOT),
        gate_label="semantics",
    )

def run_pack_audit():
    return run_validator_script(
        script_path=AUDIT_SCRIPT,
        repo_root=REPO_ROOT,
        rel_paths=[],
        gate_label="pack-audit",
    )

def main():
    parser = argparse.ArgumentParser(description="Validate ComfyUI workflow JSON.")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--pack-audit", action="store_true")
    parser.add_argument(
        "--semantics",
        action="store_true",
        help="Check example prompts and sampler defaults match pack expectations",
    )
    parser.add_argument(
        "--topology",
        action="store_true",
        help="Validate root/subgraph topology and wrapper interface consistency",
    )
    args = parser.parse_args()
    targets = expand_paths(args.paths or ["workflows"], REPO_ROOT)
    if not targets:
        sys.stdout.write("usage: validate_workflow_json.py <workflow.json> [...]\n")
        return 2
    failed = any(not validate_file(t) for t in targets)
    if args.semantics and not run_semantics(targets):
        failed = True
    if args.topology and not run_topology(targets):
        failed = True
    if args.pack_audit and not run_pack_audit():
        failed = True
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
