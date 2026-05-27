#!/usr/bin/env python3
"""Replace CheckpointLoaderSimple with split NewBie loaders in bundled workflows."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

UNET_BY_FILE = {
    "workflows/newbie-image/newbie-t2i-low.json": (
        "newbie_image_exp0.1_fp8-e4m3fn.safetensors",
        "https://huggingface.co/Kokoboyaw/NewBie-image-Exp0.1-quantized/resolve/main/newbie_image_exp0.1_fp8-e4m3fn.safetensors",
    ),
    "workflows/newbie-image/newbie-t2i-high.json": (
        "newbie_image_exp0.1_fp16.safetensors",
        "https://huggingface.co/Kokoboyaw/NewBie-image-Exp0.1-quantized/resolve/main/newbie_image_exp0.1_fp16.safetensors",
    ),
}


def split_loader_nodes(unet_name: str, unet_url: str) -> list[dict]:
    return [
        {
            "id": 576,
            "type": "UNETLoader",
            "pos": [-27700, 25010],
            "size": [400, 82],
            "flags": {},
            "order": 1,
            "mode": 0,
            "inputs": [],
            "outputs": [
                {
                    "name": "MODEL",
                    "type": "MODEL",
                    "slot_index": 0,
                    "links": [1080],
                }
            ],
            "properties": {
                "cnr_id": "comfy-core",
                "ver": "0.19.3",
                "Node name for S&R": "UNETLoader",
                "models": [
                    {
                        "name": unet_name,
                        "url": unet_url,
                        "directory": "diffusion_models",
                    }
                ],
            },
            "widgets_values": [unet_name, "default"],
            "color": "#346434",
            "bgcolor": "rgba(24,24,27,.9)",
        },
        {
            "id": 577,
            "type": "ModelSamplingAuraFlow",
            "pos": [-27700, 25110],
            "size": [400, 60],
            "flags": {},
            "order": 2,
            "mode": 0,
            "inputs": [
                {"name": "model", "type": "MODEL", "link": 1080},
            ],
            "outputs": [
                {
                    "name": "MODEL",
                    "type": "MODEL",
                    "slot_index": 0,
                    "links": [13, 944],
                }
            ],
            "properties": {
                "cnr_id": "comfy-core",
                "ver": "0.19.3",
                "Node name for S&R": "ModelSamplingAuraFlow",
            },
            "widgets_values": [6],
            "color": "#346434",
            "bgcolor": "rgba(24,24,27,.9)",
        },
        {
            "id": 578,
            "type": "DualCLIPLoader",
            "pos": [-27700, 25200],
            "size": [400, 130],
            "flags": {},
            "order": 3,
            "mode": 0,
            "inputs": [],
            "outputs": [
                {
                    "name": "CLIP",
                    "type": "CLIP",
                    "slot_index": 0,
                    "links": [1062],
                }
            ],
            "properties": {
                "cnr_id": "comfy-core",
                "ver": "0.19.3",
                "Node name for S&R": "DualCLIPLoader",
                "models": [
                    {
                        "name": "gemma_3_4b_it_bf16.safetensors",
                        "url": "https://huggingface.co/Comfy-Org/NewBie-image-Exp0.1_repackaged/resolve/main/split_files/text_encoders/gemma_3_4b_it_bf16.safetensors",
                        "directory": "text_encoders",
                    },
                    {
                        "name": "jina_clip_v2_bf16.safetensors",
                        "url": "https://huggingface.co/Comfy-Org/NewBie-image-Exp0.1_repackaged/resolve/main/split_files/text_encoders/jina_clip_v2_bf16.safetensors",
                        "directory": "text_encoders",
                    },
                ],
            },
            "widgets_values": [
                "gemma_3_4b_it_bf16.safetensors",
                "jina_clip_v2_bf16.safetensors",
                "newbie",
                "default",
            ],
            "color": "#346434",
            "bgcolor": "rgba(24,24,27,.9)",
        },
        {
            "id": 579,
            "type": "VAELoader",
            "pos": [-27700, 25360],
            "size": [400, 58],
            "flags": {},
            "order": 4,
            "mode": 0,
            "inputs": [],
            "outputs": [
                {
                    "name": "VAE",
                    "type": "VAE",
                    "slot_index": 0,
                    "links": [948],
                }
            ],
            "properties": {
                "cnr_id": "comfy-core",
                "ver": "0.19.3",
                "Node name for S&R": "VAELoader",
                "models": [
                    {
                        "name": "ae.safetensors",
                        "url": "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors",
                        "directory": "vae",
                    }
                ],
            },
            "widgets_values": ["ae.safetensors"],
            "color": "#346434",
            "bgcolor": "rgba(24,24,27,.9)",
        },
    ]


def patch_workflow(path: Path, unet_name: str, unet_url: str) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    nodes = doc.get("nodes", [])
    nodes = [n for n in nodes if n.get("type") != "CheckpointLoaderSimple"]
    insert_at = next(
        (i for i, n in enumerate(nodes) if n.get("id") == 5),
        len(nodes),
    )
    nodes[insert_at:insert_at] = split_loader_nodes(unet_name, unet_url)
    doc["nodes"] = nodes
    doc["last_node_id"] = max(doc.get("last_node_id", 0), 579)
    doc["last_link_id"] = max(doc.get("last_link_id", 0), 1080)

    links = doc.get("links", [])
    for link in links:
        if not isinstance(link, list) or len(link) < 5:
            continue
        link_id, origin_id, origin_slot, target_id, target_slot = link[:5]
        if link_id == 13:
            link[1] = 577
            link[2] = 0
        elif link_id == 944:
            link[1] = 577
            link[2] = 0
        elif link_id == 948:
            link[1] = 579
            link[2] = 0
        elif link_id == 1062:
            link[1] = 578
            link[2] = 0

    if not any(isinstance(l, list) and l[0] == 1080 for l in links):
        links.append([1080, 576, 0, 577, 0, "MODEL"])
    doc["links"] = links

    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {path.relative_to(REPO)}")


def main() -> None:
    for rel, (unet_name, unet_url) in UNET_BY_FILE.items():
        patch_workflow(REPO / rel, unet_name, unet_url)


if __name__ == "__main__":
    main()
