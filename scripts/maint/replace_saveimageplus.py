#!/usr/bin/env python3
"""One-off migration: replace LayerUtility SaveImagePlus with core SaveImage (v1.7.0)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_ROOT = REPO_ROOT / "workflows"
SAVEIMAGEPLUS_TYPE = "LayerUtility: SaveImagePlus"


def prefix_from_widgets(widgets_values: list) -> str:
    if len(widgets_values) >= 2 and isinstance(widgets_values[1], str) and widgets_values[1]:
        return widgets_values[1]
    if widgets_values and isinstance(widgets_values[0], str) and widgets_values[0]:
        return widgets_values[0]
    return "ComfyUI"


def infer_comfy_ver(data: dict) -> str:
    for node in data.get("nodes", []):
        props = node.get("properties") or {}
        if props.get("cnr_id") == "comfy-core" and props.get("ver"):
            ver = str(props["ver"])
            if ver != "1.0.90":
                return ver
    return "0.22.0"


def convert_node(node: dict, comfy_ver: str) -> bool:
    if node.get("type") != SAVEIMAGEPLUS_TYPE:
        return False

    prefix = prefix_from_widgets(node.get("widgets_values") or [])
    node["type"] = "SaveImage"
    node["inputs"] = [
        inp for inp in node.get("inputs", []) if inp.get("name") == "images"
    ]
    props = dict(node.get("properties") or {})
    props["cnr_id"] = "comfy-core"
    props["ver"] = comfy_ver
    props["Node name for S&R"] = "SaveImage"
    node["properties"] = props
    node["widgets_values"] = [prefix]
    return True


def convert_workflow(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    comfy_ver = infer_comfy_ver(data)
    changed = 0
    for node in data.get("nodes", []):
        if convert_node(node, comfy_ver):
            changed += 1
    if changed:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return changed


def main() -> int:
    total = 0
    files = 0
    for path in sorted(WORKFLOWS_ROOT.rglob("*.json")):
        n = convert_workflow(path)
        if n:
            print(f"[OK] {path.relative_to(REPO_ROOT)}: {n} node(s)")
            total += n
            files += 1
    if total == 0:
        print("[OK] No SaveImagePlus nodes found.")
        return 0
    print(f"[OK] Replaced {total} node(s) in {files} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
