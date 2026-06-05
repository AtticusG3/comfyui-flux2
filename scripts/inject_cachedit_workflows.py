#!/usr/bin/env python3
"""Insert CacheDiT optimizer nodes between UNETLoader MODEL outputs and downstream consumers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

IMAGE_OPTIMIZER = "CacheDiT_Model_Optimizer"
WAN_OPTIMIZER = "WanCacheOptimizer"
LOADER_TYPES = {"UNETLoader"}

IMAGE_WIDGETS = [True, "Auto", 0, 0, True]
WAN_WIDGETS = [True, 4, 2, True]

IMAGE_DIT_PATHS = [
    REPO_ROOT / "workflows/flux2/klein-t2i.json",
    REPO_ROOT / "workflows/flux2/klein-edit.json",
    REPO_ROOT / "workflows/z-image-turbo/z-turbo-t2i.json",
    REPO_ROOT / "workflows/z-image-turbo/z-base-t2i.json",
    REPO_ROOT / "workflows/z-anime/z-anime-t2i.json",
    REPO_ROOT / "workflows/qwen-image-edit-2511/qwen-edit-2511.json",
]

WAN_PATHS = sorted((REPO_ROOT / "workflows/wan-2-2").glob("*.json"))

TEMPLATE_PATHS = [
    REPO_ROOT / "workflows/_templates/Klein_4B_Text_to_Image.json",
    REPO_ROOT / "workflows/_templates/Klein_4B_Image_Edit.json",
    REPO_ROOT / "workflows/_templates/New_Subgraph.json",
]


def _is_list_links(links: list[Any]) -> bool:
    return bool(links) and isinstance(links[0], list)


def _get_counters(section: dict[str, Any]) -> tuple[str, str]:
    if "state" in section and isinstance(section["state"], dict):
        return "lastNodeId", "lastLinkId"
    return "last_node_id", "last_link_id"


def _read_counter(section: dict[str, Any], key: str) -> int:
    if key in section:
        return int(section[key])
    state = section.get("state")
    if isinstance(state, dict) and key in state:
        return int(state[key])
    return 0


def _write_counter(section: dict[str, Any], key: str, value: int) -> None:
    if "state" in section and isinstance(section["state"], dict) and key in section["state"]:
        section["state"][key] = value
    elif key in section:
        section[key] = value
    elif "state" in section and isinstance(section["state"], dict):
        section["state"][key] = value
    else:
        section[key] = value


def _node_by_id(nodes: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(n["id"]): n for n in nodes}


def _optimizer_present(nodes: list[dict[str, Any]]) -> bool:
    return any(n.get("type") in {IMAGE_OPTIMIZER, WAN_OPTIMIZER} for n in nodes)


def _build_optimizer_node(
    node_id: int,
    optimizer_type: str,
    link_in: int,
    link_out: int,
    loader: dict[str, Any],
) -> dict[str, Any]:
    pos = loader.get("pos", [0, 0])
    widgets = WAN_WIDGETS if optimizer_type == WAN_OPTIMIZER else IMAGE_WIDGETS
    display = (
        "CacheDiT Wan Accelerator"
        if optimizer_type == WAN_OPTIMIZER
        else "CacheDiT Accelerator"
    )
    return {
        "id": node_id,
        "type": optimizer_type,
        "pos": [pos[0] + 300, pos[1]],
        "size": [340, 186 if optimizer_type == IMAGE_OPTIMIZER else 150],
        "flags": {},
        "order": int(loader.get("order", 0)) + 1,
        "mode": 0,
        "inputs": [
            {
                "name": "model",
                "type": "MODEL",
                "link": link_in,
            }
        ],
        "outputs": [
            {
                "name": "optimized_model",
                "type": "MODEL",
                "links": [link_out],
            }
        ],
        "title": display,
        "properties": {
            "Node name for S&R": optimizer_type,
        },
        "widgets_values": widgets,
        "color": "#2a4a3a",
        "bgcolor": "rgba(24,24,27,.9)",
    }


def _replace_input_link(node: dict[str, Any], old_link: int, new_link: int) -> None:
    for inp in node.get("inputs", []):
        if inp.get("link") == old_link:
            inp["link"] = new_link


def _inject_list_graph(section: dict[str, Any], optimizer_type: str) -> int:
    nodes: list[dict[str, Any]] = section.get("nodes", [])
    links: list[list[Any]] = section.get("links", [])
    if not nodes or not links or not _is_list_links(links):
        return 0

    node_key, link_key = _get_counters(section)
    node_id = _read_counter(section, node_key)
    link_id = _read_counter(section, link_key)
    by_id = _node_by_id(nodes)
    injected = 0

    for loader in nodes:
        if loader.get("type") not in LOADER_TYPES:
            continue
        outputs = loader.get("outputs") or []
        model_out = next((o for o in outputs if o.get("type") == "MODEL"), None)
        if not model_out or not model_out.get("links"):
            continue

        for old_link in list(model_out.get("links", [])):
            link_row = next((l for l in links if l[0] == old_link), None)
            if not link_row or link_row[5] != "MODEL":
                continue

            _lid, origin_id, origin_slot, target_id, target_slot, _typ = link_row
            if int(origin_id) != int(loader["id"]):
                continue

            target = by_id.get(int(target_id))
            if target and target.get("type") in {IMAGE_OPTIMIZER, WAN_OPTIMIZER}:
                continue

            node_id += 1
            link_in = link_id + 1
            link_out = link_id + 2
            link_id += 2

            model_out["links"] = [
                link_in if x == old_link else x for x in model_out["links"]
            ]

            link_row[0] = link_in
            link_row[3] = node_id
            link_row[4] = 0

            links.append([link_out, node_id, 0, target_id, target_slot, "MODEL"])

            if target:
                _replace_input_link(target, old_link, link_out)

            nodes.append(
                _build_optimizer_node(node_id, optimizer_type, link_in, link_out, loader)
            )
            by_id[node_id] = nodes[-1]
            injected += 1

    if injected:
        _write_counter(section, node_key, node_id)
        _write_counter(section, link_key, link_id)
    return injected


def _inject_dict_graph(section: dict[str, Any], optimizer_type: str) -> int:
    nodes: list[dict[str, Any]] = section.get("nodes", [])
    links: list[dict[str, Any]] = section.get("links", [])
    if not nodes or not links or _is_list_links(links):
        return 0

    node_key, link_key = _get_counters(section)
    node_id = _read_counter(section, node_key)
    link_id = _read_counter(section, link_key)
    by_id = _node_by_id(nodes)
    injected = 0

    for loader in nodes:
        if loader.get("type") not in LOADER_TYPES:
            continue
        outputs = loader.get("outputs") or []
        model_out = next((o for o in outputs if o.get("type") == "MODEL"), None)
        if not model_out or not model_out.get("links"):
            continue

        for old_link in list(model_out.get("links", [])):
            link_row = next((l for l in links if l.get("id") == old_link), None)
            if not link_row or link_row.get("type") != "MODEL":
                continue
            if int(link_row.get("origin_id", -1)) != int(loader["id"]):
                continue

            target_id = int(link_row["target_id"])
            target_slot = int(link_row.get("target_slot", 0))
            target = by_id.get(target_id)
            if target and target.get("type") in {IMAGE_OPTIMIZER, WAN_OPTIMIZER}:
                continue

            node_id += 1
            link_in = link_id + 1
            link_out = link_id + 2
            link_id += 2

            model_out["links"] = [
                link_in if x == old_link else x for x in model_out["links"]
            ]

            link_row["id"] = link_in
            link_row["target_id"] = node_id
            link_row["target_slot"] = 0

            links.append(
                {
                    "id": link_out,
                    "origin_id": node_id,
                    "origin_slot": 0,
                    "target_id": target_id,
                    "target_slot": target_slot,
                    "type": "MODEL",
                }
            )

            if target:
                _replace_input_link(target, old_link, link_out)

            nodes.append(
                _build_optimizer_node(node_id, optimizer_type, link_in, link_out, loader)
            )
            by_id[node_id] = nodes[-1]
            injected += 1

    if injected:
        _write_counter(section, node_key, node_id)
        _write_counter(section, link_key, link_id)
    return injected


def inject_section(section: dict[str, Any], optimizer_type: str) -> int:
    if _optimizer_present(section.get("nodes", [])):
        # Still process if only partial; per-loader skip handles duplicates.
        pass
    links = section.get("links", [])
    if not links:
        return 0
    if _is_list_links(links):
        return _inject_list_graph(section, optimizer_type)
    return _inject_dict_graph(section, optimizer_type)


def inject_workflow(data: dict[str, Any], optimizer_type: str) -> int:
    total = 0
    if "nodes" in data and "links" in data:
        total += inject_section(data, optimizer_type)

    subgraphs = data.get("definitions", {}).get("subgraphs", [])
    for subgraph in subgraphs:
        total += inject_section(subgraph, optimizer_type)
    return total


def process_file(path: Path, optimizer_type: str, write: bool) -> int:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    before = json.dumps(data, sort_keys=True)
    count = inject_workflow(data, optimizer_type)
    if count == 0:
        print(f"[SKIP] {path.relative_to(REPO_ROOT)}: no UNETLoader MODEL links to patch")
        return 0
    after = json.dumps(data, sort_keys=True)
    if before == after:
        print(f"[SKIP] {path.relative_to(REPO_ROOT)}: already patched")
        return 0
    if write:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] {path.relative_to(REPO_ROOT)}: injected {count} optimizer node(s)")
    else:
        print(f"[DRY] {path.relative_to(REPO_ROOT)}: would inject {count} optimizer node(s)")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Persist workflow changes")
    parser.add_argument("--templates", action="store_true", help="Also patch _templates donors")
    args = parser.parse_args()

    total = 0
    for path in IMAGE_DIT_PATHS:
        if path.is_file():
            total += process_file(path, IMAGE_OPTIMIZER, args.write)

    for path in WAN_PATHS:
        total += process_file(path, WAN_OPTIMIZER, args.write)

    if args.templates:
        for path in TEMPLATE_PATHS:
            if path.is_file():
                total += process_file(path, IMAGE_OPTIMIZER, args.write)

    if total == 0:
        print("[WARN] No workflows modified")
        return 1
    print(f"[INFO] Total optimizer injections: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
