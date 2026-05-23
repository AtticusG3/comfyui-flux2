#!/usr/bin/env python3
"""Graft enhancement subgraph definitions from golden workflow onto plain pack workflows."""
from __future__ import annotations
import argparse
import json
import copy
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DONOR = REPO / "workflows/sdxl-lightning/sdxl-lightning-t2i.json"
TEMPLATES = REPO / "workflows/_templates"

def load_wf(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def get_subgraphs(wf: dict) -> list:
    defs = wf.setdefault("definitions", {})
    if "subgraphs" not in defs:
        defs["subgraphs"] = []
    return defs["subgraphs"]

def has_enhancement(wf: dict) -> bool:
    blob = json.dumps(wf)
    return "SeedVR2" in blob and "DetailDaemon" in blob

def merge_donor_subgraphs(target: dict, donor: dict) -> None:
    t_subs = get_subgraphs(target)
    names = {s.get("name") for s in t_subs}
    for sg in get_subgraphs(donor):
        if sg.get("name") not in names:
            t_subs.append(copy.deepcopy(sg))

def merge_template_subgraphs(target: dict) -> None:
    t_subs = get_subgraphs(target)
    names = {s.get("name") for s in t_subs}
    for path in sorted(TEMPLATES.glob("*.json")):
        if path.name.startswith("HiRes") or path.name == "README.md":
            continue
        sg = json.loads(path.read_text(encoding="utf-8"))
        if sg.get("name") not in names:
            t_subs.append(sg)

def patch_checkpoint(wf: dict, checkpoint: str) -> None:
    for node in wf.get("nodes", []):
        if node.get("type") == "CheckpointLoaderSimple":
            wv = node.get("widgets_values") or []
            if wv:
                wv[0] = checkpoint
            node["widgets_values"] = wv

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", type=Path, required=True)
    ap.add_argument("--checkpoint", default="")
    ap.add_argument("--donor", type=Path, default=DONOR)
    args = ap.parse_args()
    target_path = args.workflow if args.workflow.is_absolute() else REPO / args.workflow
    target = load_wf(target_path)
    if has_enhancement(target):
        print("[SKIP] already has enhancement stack:", target_path.name)
        return
    donor = load_wf(args.donor if args.donor.is_absolute() else REPO / args.donor)
    merge_donor_subgraphs(target, donor)
    merge_template_subgraphs(target)
    if args.checkpoint:
        patch_checkpoint(target, args.checkpoint)
    target_path.write_text(json.dumps(target, indent=2), encoding="utf-8")
    print("[OK] merged subgraph defs into", target_path)

if __name__ == "__main__":
    main()
