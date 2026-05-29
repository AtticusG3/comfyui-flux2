#!/usr/bin/env python3
"""Validate ComfyUI workflow topology, including embedded subgraph wrappers.

Checks performed:
- Link endpoint integrity for root graph and embedded subgraphs.
- Node input/output link references point to real link ids.
- Optional UUID wrapper parity checks against embedded subgraph interfaces.
- Optional wrapper auto-fix mode to sync wrapper ports from embedded definitions.

ASCII-only output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lib.workflow_links import link_fields
from lib.workflow_links import links_kind
from lib.workflow_subgraph_ports import check_wrapper_interfaces
from lib.workflow_subgraph_ports import realign_orphan_wrapper_links
from lib.workflow_subgraph_ports import sync_all_wrappers
from lib.workflow_validate_cli import emit
from lib.workflow_validate_cli import expand_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
PSEUDO_NODE_IDS = {-10, -20}


def _node_ids(graph: dict[str, Any]) -> set[Any]:
    return {
        n.get("id")
        for n in graph.get("nodes", [])
        if isinstance(n, dict) and "id" in n
    }


def _check_graph_links(graph: dict[str, Any], *, allow_pseudo: bool) -> list[str]:
    errs: list[str] = []
    links = graph.get("links")
    if not isinstance(links, list):
        return ["links is not a list"]
    kind = links_kind(links)
    if kind is None:
        return ["links[0] is neither tuple nor object"]
    ids = _node_ids(graph)
    link_ids: set[Any] = set()
    for idx, link in enumerate(links):
        lid, src, dst = link_fields(link, kind)
        if lid is None:
            errs.append(f"links[{idx}] malformed")
            continue
        if lid in link_ids:
            errs.append(f"duplicate link id {lid}")
        link_ids.add(lid)
        src_ok = src in ids or (allow_pseudo and src in PSEUDO_NODE_IDS)
        dst_ok = dst in ids or (allow_pseudo and dst in PSEUDO_NODE_IDS)
        if not src_ok:
            errs.append(f"links[{idx}] dangling source node {src}")
        if not dst_ok:
            errs.append(f"links[{idx}] dangling target node {dst}")
    return errs


def _graph_link_id_set(graph: dict[str, Any]) -> set[Any]:
    links = graph.get("links")
    if not isinstance(links, list):
        return set()
    kind = links_kind(links)
    if kind is None:
        return set()
    out: set[Any] = set()
    for link in links:
        lid, _, _ = link_fields(link, kind)
        if lid is not None:
            out.add(lid)
    return out


def _check_node_references(graph: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    link_ids = _graph_link_id_set(graph)
    for node in graph.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        for inp in node.get("inputs") or []:
            if not isinstance(inp, dict):
                continue
            lid = inp.get("link")
            if lid is not None and lid not in link_ids:
                errs.append(f"node {node_id} input {inp.get('name')!r} missing link {lid}")
        for out in node.get("outputs") or []:
            if not isinstance(out, dict):
                continue
            lids = out.get("links")
            if lids is None:
                continue
            if not isinstance(lids, list):
                errs.append(f"node {node_id} output {out.get('name')!r} links is not list")
                continue
            for lid in lids:
                if lid not in link_ids:
                    errs.append(
                        f"node {node_id} output {out.get('name')!r} missing link {lid}"
                    )
    return errs




def _check_lazy_execution_paths(graph: dict[str, Any], *, allow_pseudo: bool) -> list[str]:
    """Validate required upstream links by reverse traversal from terminal outputs.

    This mirrors lazy execution: start from graph sinks and walk backward through
    input links. Any broken link on an actually-required path fails.
    """
    errs: list[str] = []
    links = graph.get("links")
    nodes = graph.get("nodes")
    if not isinstance(links, list) or not isinstance(nodes, list):
        return errs
    kind = links_kind(links)
    if kind is None:
        return errs

    by_id = {
        n.get("id"): n
        for n in nodes
        if isinstance(n, dict) and "id" in n
    }

    link_by_id: dict[Any, tuple[Any, Any, Any, Any]] = {}
    incoming: dict[Any, list[Any]] = {}
    for link in links:
        if kind == "tuple":
            if not isinstance(link, list) or len(link) < 5:
                continue
            lid, src, src_slot, dst, dst_slot = link[0], link[1], link[2], link[3], link[4]
        else:
            if not isinstance(link, dict):
                continue
            lid = link.get("id")
            src = link.get("origin_id")
            src_slot = link.get("origin_slot")
            dst = link.get("target_id")
            dst_slot = link.get("target_slot")
        if lid is None:
            continue
        link_by_id[lid] = (src, src_slot, dst, dst_slot)
        incoming.setdefault(dst, []).append(lid)

    # Terminal targets: output pseudo node for subgraphs, otherwise sink nodes.
    terminals: list[Any] = []
    if allow_pseudo and -20 in incoming:
        terminals.append(-20)
    else:
        for nid, node in by_id.items():
            outs = node.get("outputs") or []
            has_downstream = False
            for out in outs:
                if not isinstance(out, dict):
                    continue
                lids = out.get("links")
                if isinstance(lids, list) and lids:
                    has_downstream = True
                    break
            if not has_downstream and (node.get("inputs") or []):
                terminals.append(nid)

    stack: list[Any] = []
    seen_nodes: set[Any] = set()

    for t in terminals:
        stack.append(t)

    while stack:
        nid = stack.pop()
        if nid in seen_nodes:
            continue
        seen_nodes.add(nid)

        # Follow incoming links to this node and validate them as required path.
        for lid in incoming.get(nid, []):
            rec = link_by_id.get(lid)
            if rec is None:
                errs.append(f"lazy path missing link record {lid}")
                continue
            src, src_slot, dst, dst_slot = rec

            # Validate target side consistency for required link.
            if dst in by_id:
                dst_node = by_id[dst]
                dst_inputs = dst_node.get("inputs") or []
                if not isinstance(dst_slot, int) or dst_slot < 0 or dst_slot >= len(dst_inputs):
                    errs.append(f"lazy link {lid} target slot out of range on node {dst}")
                else:
                    inp = dst_inputs[dst_slot]
                    if isinstance(inp, dict) and inp.get("link") != lid:
                        errs.append(f"lazy link {lid} target node {dst} slot {dst_slot} has input.link={inp.get('link')}")

            # Validate source side consistency for required link.
            if src in by_id:
                src_node = by_id[src]
                src_outputs = src_node.get("outputs") or []
                if not isinstance(src_slot, int) or src_slot < 0 or src_slot >= len(src_outputs):
                    errs.append(f"lazy link {lid} source slot out of range on node {src}")
                else:
                    out = src_outputs[src_slot]
                    if isinstance(out, dict):
                        lids = out.get("links")
                        if isinstance(lids, list) and lid not in lids:
                            errs.append(f"lazy link {lid} missing from source node {src} slot {src_slot} output.links")

                stack.append(src)
            elif not (allow_pseudo and src in PSEUDO_NODE_IDS):
                errs.append(f"lazy link {lid} has missing source node {src}")

    return errs
def _check_slot_link_alignment(graph: dict[str, Any], *, allow_pseudo: bool) -> list[str]:
    errs: list[str] = []
    links = graph.get("links")
    nodes = graph.get("nodes")
    if not isinstance(links, list) or not isinstance(nodes, list):
        return errs
    kind = links_kind(links)
    if kind is None:
        return errs

    by_id = {
        n.get("id"): n
        for n in nodes
        if isinstance(n, dict) and "id" in n
    }
    pseudo_ok = PSEUDO_NODE_IDS if allow_pseudo else set()

    link_target = {}
    link_origin = {}
    for idx, link in enumerate(links):
        if kind == "tuple":
            if not isinstance(link, list) or len(link) < 5:
                continue
            lid, src, src_slot, dst, dst_slot = link[0], link[1], link[2], link[3], link[4]
        else:
            if not isinstance(link, dict):
                continue
            lid = link.get("id")
            src = link.get("origin_id")
            src_slot = link.get("origin_slot")
            dst = link.get("target_id")
            dst_slot = link.get("target_slot")
        if lid is None:
            continue
        link_target[lid] = (dst, dst_slot)
        link_origin[lid] = (src, src_slot)

    for lid, (dst, dst_slot) in link_target.items():
        if dst in pseudo_ok:
            continue
        node = by_id.get(dst)
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs") or []
        if not isinstance(dst_slot, int) or dst_slot < 0 or dst_slot >= len(inputs):
            errs.append(f"link {lid} targets node {dst} input slot {dst_slot} out of range")
            continue
        inp = inputs[dst_slot]
        if isinstance(inp, dict):
            if inp.get("link") != lid:
                errs.append(
                    f"link {lid} targets node {dst} slot {dst_slot} but input.link is {inp.get('link')}"
                )

    for lid, (src, src_slot) in link_origin.items():
        if src in pseudo_ok:
            continue
        node = by_id.get(src)
        if not isinstance(node, dict):
            continue
        outputs = node.get("outputs") or []
        if not isinstance(src_slot, int) or src_slot < 0 or src_slot >= len(outputs):
            errs.append(f"link {lid} originates node {src} output slot {src_slot} out of range")
            continue
        out = outputs[src_slot]
        if isinstance(out, dict):
            lids = out.get("links")
            if isinstance(lids, list) and lid not in lids:
                errs.append(
                    f"link {lid} originates node {src} slot {src_slot} but not listed in output.links"
                )
    return errs


def validate_doc(doc: dict[str, Any], *, check_wrapper: bool = False) -> tuple[bool, list[str]]:
    if not isinstance(doc, dict):
        return False, ["top-level JSON must be object"]
    if not isinstance(doc.get("nodes"), list) or not isinstance(doc.get("links"), list):
        return False, ["not a UI workflow graph (missing nodes/links arrays)"]

    errs: list[str] = []
    root_graph = {"nodes": doc.get("nodes", []), "links": doc.get("links", [])}
    errs.extend(_check_graph_links(root_graph, allow_pseudo=False))
    errs.extend(_check_node_references(root_graph))
    errs.extend(_check_slot_link_alignment(root_graph, allow_pseudo=False))
    errs.extend(_check_lazy_execution_paths(root_graph, allow_pseudo=False))

    defs = doc.get("definitions", {})
    subgraphs = defs.get("subgraphs", []) if isinstance(defs, dict) else []
    for sg in subgraphs:
        if not isinstance(sg, dict):
            continue
        name = sg.get("name") or sg.get("id") or "<subgraph>"
        sub_graph = {"nodes": sg.get("nodes", []), "links": sg.get("links", [])}
        local_errs = _check_graph_links(sub_graph, allow_pseudo=True)
        local_errs.extend(_check_node_references(sub_graph))
        local_errs.extend(_check_slot_link_alignment(sub_graph, allow_pseudo=True))
        local_errs.extend(_check_lazy_execution_paths(sub_graph, allow_pseudo=True))
        errs.extend([f"{name}: {msg}" for msg in local_errs])

    if check_wrapper:
        errs.extend(check_wrapper_interfaces(doc))
    return len(errs) == 0, errs


def validate_file(path: Path, *, check_wrapper: bool = False) -> tuple[bool, list[str]]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return False, [f"parse error: {exc}"]
    return validate_doc(doc, check_wrapper=check_wrapper)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate topology for workflows and embedded subgraphs."
    )
    parser.add_argument("paths", nargs="*", help="Workflow files or directories")
    parser.add_argument(
        "--check-wrapper",
        action="store_true",
        help="Validate wrapper UUID node interfaces against embedded subgraph ports",
    )
    parser.add_argument(
        "--fix-wrapper",
        action="store_true",
        help="Sync wrapper ports from embedded subgraph interfaces before validation",
    )
    args = parser.parse_args()
    targets = expand_paths(args.paths or ["workflows"], REPO_ROOT)
    if not targets:
        sys.stdout.write("usage: validate_workflow_topology.py <workflow.json> [...]\n")
        return 2

    failed = False
    for p in targets:
        rel = str(p.relative_to(REPO_ROOT) if p.is_relative_to(REPO_ROOT) else p)

        if args.fix_wrapper:
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                emit(rel, "topology-fix", False, f"parse error: {exc}")
                failed = True
                continue
            changed_nodes, link_fixes = sync_all_wrappers(doc)
            orphan_link_fixes = realign_orphan_wrapper_links(doc)
            all_link_fixes = {**link_fixes, **orphan_link_fixes}
            write_needed = bool(changed_nodes or all_link_fixes)
            if write_needed:
                p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            msg_parts: list[str] = []
            if changed_nodes:
                msg_parts.append(f"synced wrapper nodes: {', '.join(changed_nodes)}")
            if all_link_fixes:
                total_links = sum(all_link_fixes.values())
                detail = ", ".join(f"{nid}:{count}" for nid, count in sorted(all_link_fixes.items()))
                msg_parts.append(f"links realigned: {total_links} ({detail})")
            if msg_parts:
                emit(rel, "topology-fix", True, "; ".join(msg_parts))
            else:
                emit(rel, "topology-fix", True, "no wrapper drift")

        ok, errs = validate_file(p, check_wrapper=(args.check_wrapper or args.fix_wrapper))
        emit(rel, "topology", ok, "; ".join(errs[:4]) if errs else "")
        if not ok and len(errs) > 4:
            emit(rel, "topology-detail", False, f"+{len(errs) - 4} more")
        if not ok:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
