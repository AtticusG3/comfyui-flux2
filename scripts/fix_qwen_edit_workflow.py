#!/usr/bin/env python3
"""Normalize Qwen Image Edit 2511 bundled workflow model references."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / "workflows/qwen-image-edit-2511/qwen-edit-2511.json"

UNET_NVFP4 = "qwen_image_edit_2511_nvfp4.safetensors"
UNET_NVFP4_URL = (
    "https://huggingface.co/Bedovyy/Qwen-Image-Edit-2511-NVFP4/resolve/main/"
    "qwen_image_edit_2511_nvfp4.safetensors"
)
VAE_NAME = "qwen_image_vae.safetensors"
VAE_URL = (
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/"
    "split_files/vae/qwen_image_vae.safetensors"
)
TE_NAME = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
TE_URL = (
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/"
    "split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"
)


def patch_node(node: dict) -> None:
    node_type = node.get("type", "")
    if node_type == "UNETLoader":
        node["widgets_values"] = [UNET_NVFP4, "default"]
        props = node.setdefault("properties", {})
        props["models"] = [
            {
                "name": UNET_NVFP4,
                "url": UNET_NVFP4_URL,
                "directory": "diffusion_models",
            }
        ]
    elif node_type == "CLIPLoader":
        wv = list(node.get("widgets_values") or [])
        if wv:
            wv[0] = TE_NAME
        if len(wv) < 2:
            wv.extend(["qwen_image", "default"])
        node["widgets_values"] = wv[:3]
        props = node.setdefault("properties", {})
        props["models"] = [
            {
                "name": TE_NAME,
                "url": TE_URL,
                "directory": "text_encoders",
            }
        ]
    elif node_type == "VAELoader":
        node["widgets_values"] = [VAE_NAME]
        props = node.setdefault("properties", {})
        props["models"] = [
            {
                "name": VAE_NAME,
                "url": VAE_URL,
                "directory": "vae",
            }
        ]
    elif node_type == "SaveImage":
        node["widgets_values"] = ["qwen_image_edit_2511/"]


def main() -> None:
    data = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    for node in data.get("nodes", []):
        patch_node(node)
    WORKFLOW.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {WORKFLOW.relative_to(REPO)}")


if __name__ == "__main__":
    main()
