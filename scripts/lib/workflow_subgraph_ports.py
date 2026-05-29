"""Shared helpers for UUID subgraph wrapper port parity and sync."""
from __future__ import annotations

import re
from typing import Any

from lib.workflow_links import links_kind

UUID_TYPE_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _subgraph_index(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    defs = doc.get("definitions", {})
    subs = defs.get("subgraphs", []) if isinstance(defs, dict) else []
    return {
        sg.get("id"): sg
        for sg in subs
        if isinstance(sg, dict) and isinstance(sg.get("id"), str)
    }


def find_subgraph(
    doc: dict[str, Any], subgraph_id: str | None, subgraph_name: str | None
) -> dict[str, Any]:
    defs = doc.get("definitions", {})
    subs = defs.get("subgraphs", []) if isinstance(defs, dict) else []
    cands = [s for s in subs if isinstance(s, dict)]
    if subgraph_id:
        for subgraph in cands:
            if subgraph.get("id") == subgraph_id:
                return subgraph
        raise ValueError(f"subgraph id not found: {subgraph_id}")
    if subgraph_name:
        matches = [subgraph for subgraph in cands if subgraph.get("name") == subgraph_name]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f"subgraph name not found: {subgraph_name}")
        raise ValueError(f"subgraph name is ambiguous: {subgraph_name}")
    raise ValueError("provide --subgraph-id or --subgraph-name")


def find_wrapper_node(doc: dict[str, Any], subgraph_id: str) -> dict[str, Any]:
    for node in doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if isinstance(node_type, str) and UUID_TYPE_RE.match(node_type) and node_type == subgraph_id:
            return node
    raise ValueError(f"wrapper node for subgraph id not found in root graph: {subgraph_id}")


def build_input_ports(
    sub_inputs: list[dict[str, Any]], old_inputs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_name = {
        item.get("name"): item
        for item in old_inputs
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    output: list[dict[str, Any]] = []
    for sub_input in sub_inputs:
        if not isinstance(sub_input, dict):
            continue
        name = sub_input.get("name")
        input_type = sub_input.get("type")
        old = by_name.get(name, {})
        label = sub_input.get("label") or sub_input.get("localized_name") or old.get("label")
        entry: dict[str, Any] = {
            "name": name if isinstance(name, str) else "",
            "type": input_type if isinstance(input_type, str) else "*",
            "link": old.get("link") if isinstance(old, dict) else None,
        }
        if isinstance(label, str) and label:
            entry["label"] = label
        if "widget" in old:
            entry["widget"] = old["widget"]
        output.append(entry)
    return output


def build_output_ports(
    sub_outputs: list[dict[str, Any]], old_outputs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_name = {
        item.get("name"): item
        for item in old_outputs
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    output: list[dict[str, Any]] = []
    for sub_output in sub_outputs:
        if not isinstance(sub_output, dict):
            continue
        name = sub_output.get("name")
        output_type = sub_output.get("type")
        old = by_name.get(name, {})
        label = sub_output.get("label") or sub_output.get("localized_name") or old.get("label")
        links = old.get("links") if isinstance(old.get("links"), list) else []
        entry: dict[str, Any] = {
            "name": name if isinstance(name, str) else "",
            "type": output_type if isinstance(output_type, str) else "*",
            "links": links,
        }
        if isinstance(label, str) and label:
            entry["label"] = label
        output.append(entry)
    return output


def _input_slot_for_link(wrapper: dict[str, Any], link_id: Any) -> int | None:
    for idx, inp in enumerate(wrapper.get("inputs") or []):
        if isinstance(inp, dict) and inp.get("link") == link_id:
            return idx
    return None


def _output_slot_for_link(wrapper: dict[str, Any], link_id: Any) -> int | None:
    for idx, out in enumerate(wrapper.get("outputs") or []):
        if not isinstance(out, dict):
            continue
        lids = out.get("links")
        if isinstance(lids, list) and link_id in lids:
            return idx
    return None


def realign_wrapper_link_slots(doc: dict[str, Any], wrapper: dict[str, Any]) -> int:
    """Align root link origin_slot/target_slot with wrapper port indices after port sync."""
    links = doc.get("links")
    if not isinstance(links, list):
        return 0
    node_id = wrapper.get("id")
    if node_id is None:
        return 0

    kind = links_kind(links)
    if kind is None:
        return 0

    fixed = 0
    for link in links:
        if kind == "tuple":
            if not isinstance(link, list) or len(link) < 5:
                continue
            link_id = link[0]
            if link[3] == node_id:
                slot = _input_slot_for_link(wrapper, link_id)
                if slot is not None and link[4] != slot:
                    link[4] = slot
                    fixed += 1
            if link[1] == node_id:
                slot = _output_slot_for_link(wrapper, link_id)
                if slot is not None and link[2] != slot:
                    link[2] = slot
                    fixed += 1
            continue
        if not isinstance(link, dict):
            continue
        link_id = link.get("id")
        if link_id is None:
            continue
        if link.get("target_id") == node_id:
            slot = _input_slot_for_link(wrapper, link_id)
            if slot is not None and link.get("target_slot") != slot:
                link["target_slot"] = slot
                fixed += 1
        if link.get("origin_id") == node_id:
            slot = _output_slot_for_link(wrapper, link_id)
            if slot is not None and link.get("origin_slot") != slot:
                link["origin_slot"] = slot
                fixed += 1
    return fixed


def realign_all_wrapper_links(doc: dict[str, Any]) -> dict[str, int]:
    """Realign root links for every UUID wrapper node. Returns node_id -> links fixed."""
    fixed_by_node: dict[str, int] = {}
    for node in doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if not isinstance(node_type, str) or not UUID_TYPE_RE.match(node_type):
            continue
        count = realign_wrapper_link_slots(doc, node)
        if count:
            fixed_by_node[str(node.get("id"))] = count
    return fixed_by_node


def realign_orphan_wrapper_links(doc: dict[str, Any]) -> dict[str, int]:
    """Realign links for UUID wrappers with no embedded subgraph definition."""
    by_id = _subgraph_index(doc)
    fixed_by_node: dict[str, int] = {}
    for node in doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if not isinstance(node_type, str) or not UUID_TYPE_RE.match(node_type):
            continue
        if by_id.get(node_type) is not None:
            continue
        count = realign_wrapper_link_slots(doc, node)
        if count:
            fixed_by_node[str(node.get("id"))] = count
    return fixed_by_node


def sync_one_wrapper(
    doc: dict[str, Any], subgraph: dict[str, Any]
) -> tuple[int, int, int, bool]:
    """Sync one wrapper from its subgraph. Returns (old_in, old_out, links_fixed, changed)."""
    subgraph_id = subgraph.get("id")
    if not isinstance(subgraph_id, str):
        raise ValueError("subgraph id missing")
    wrapper = find_wrapper_node(doc, subgraph_id)
    old_inputs = wrapper.get("inputs") or []
    old_outputs = wrapper.get("outputs") or []
    sub_inputs = subgraph.get("inputs") or []
    sub_outputs = subgraph.get("outputs") or []

    new_inputs = build_input_ports(sub_inputs, old_inputs)
    new_outputs = build_output_ports(sub_outputs, old_outputs)
    ports_changed = new_inputs != old_inputs or new_outputs != old_outputs
    if ports_changed:
        wrapper["inputs"] = new_inputs
        wrapper["outputs"] = new_outputs
    links_fixed = realign_wrapper_link_slots(doc, wrapper)
    changed = ports_changed or links_fixed > 0
    return len(old_inputs), len(old_outputs), links_fixed, changed


def sync_all_wrappers(doc: dict[str, Any]) -> tuple[list[str], dict[str, int]]:
    """Sync every UUID wrapper that has an embedded subgraph definition."""
    by_id = _subgraph_index(doc)
    changed: list[str] = []
    link_fixes: dict[str, int] = {}
    for node in doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if not isinstance(node_type, str) or not UUID_TYPE_RE.match(node_type):
            continue
        subgraph = by_id.get(node_type)
        if subgraph is None:
            continue
        _, _, links_fixed, node_changed = sync_one_wrapper(doc, subgraph)
        node_id = str(node.get("id"))
        if links_fixed:
            link_fixes[node_id] = links_fixed
        if node_changed:
            changed.append(node_id)
    return changed, link_fixes


def check_wrapper_interfaces(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    by_id = _subgraph_index(doc)
    for node in doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if not isinstance(node_type, str) or not UUID_TYPE_RE.match(node_type):
            continue
        subgraph = by_id.get(node_type)
        if subgraph is None:
            continue
        node_inputs = node.get("inputs") or []
        node_outputs = node.get("outputs") or []
        sub_inputs = subgraph.get("inputs") or []
        sub_outputs = subgraph.get("outputs") or []
        if len(node_inputs) != len(sub_inputs):
            errs.append(
                f"wrapper {node.get('id')} input count {len(node_inputs)} != subgraph {len(sub_inputs)}"
            )
        if len(node_outputs) != len(sub_outputs):
            errs.append(
                f"wrapper {node.get('id')} output count {len(node_outputs)} != subgraph {len(sub_outputs)}"
            )
        for idx, (node_input, sub_input) in enumerate(zip(node_inputs, sub_inputs)):
            if not isinstance(node_input, dict) or not isinstance(sub_input, dict):
                continue
            node_type_name = node_input.get("type")
            sub_type_name = sub_input.get("type")
            if (
                node_type_name != "*"
                and sub_type_name != "*"
                and node_type_name != sub_type_name
            ):
                errs.append(
                    f"wrapper {node.get('id')} input[{idx}] type {node_type_name!r} != subgraph {sub_type_name!r}"
                )
        for idx, (node_output, sub_output) in enumerate(zip(node_outputs, sub_outputs)):
            if not isinstance(node_output, dict) or not isinstance(sub_output, dict):
                continue
            node_type_name = node_output.get("type")
            sub_type_name = sub_output.get("type")
            if (
                node_type_name != "*"
                and sub_type_name != "*"
                and node_type_name != sub_type_name
            ):
                errs.append(
                    f"wrapper {node.get('id')} output[{idx}] type {node_type_name!r} != subgraph {sub_type_name!r}"
                )
    return errs
