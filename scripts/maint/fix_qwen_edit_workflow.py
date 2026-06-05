#!/usr/bin/env python3
"""Normalize Qwen Image Edit 2511 bundled workflow model references."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
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
TE_ALT_URL = (
    "https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/"
    "split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"
)
LORA_NAME = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
LORA_URL = (
    "https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/"
    "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
)
BF16_UNET = "qwen_image_edit_2511_bf16.safetensors"
BF16_UNET_URL = (
    "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/"
    "split_files/diffusion_models/qwen_image_edit_2511_bf16.safetensors"
)
COMFY_ORG_NVFP4_URL = (
    "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/"
    "split_files/diffusion_models/qwen_image_edit_2511_nvfp4.safetensors"
)


def replace_strings(value: object) -> object:
    if isinstance(value, str):
        return (
            value.replace(BF16_UNET_URL, UNET_NVFP4_URL)
            .replace(COMFY_ORG_NVFP4_URL, UNET_NVFP4_URL)
            .replace(BF16_UNET, UNET_NVFP4)
            .replace(TE_ALT_URL, TE_URL)
        )
    if isinstance(value, list):
        return [replace_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_strings(item) for key, item in value.items()}
    return value


def model_prop(name: str, url: str, directory: str) -> list[dict[str, str]]:
    return [{"name": name, "url": url, "directory": directory}]


def walk_nodes(workflow: dict) -> list[dict]:
    nodes = list(workflow.get("nodes", []))
    for subgraph in workflow.get("definitions", {}).get("subgraphs", []):
        nodes.extend(subgraph.get("nodes", []))
    return nodes


def patch_node(node: dict) -> None:
    node_type = node.get("type", "")
    if node_type == "UNETLoader":
        node["widgets_values"] = [UNET_NVFP4, "default"]
        props = node.setdefault("properties", {})
        props["models"] = model_prop(UNET_NVFP4, UNET_NVFP4_URL, "diffusion_models")
    elif node_type == "CLIPLoader":
        wv = list(node.get("widgets_values") or [])
        if wv:
            wv[0] = TE_NAME
        if len(wv) < 2:
            wv.extend(["qwen_image", "default"])
        node["widgets_values"] = wv[:3]
        props = node.setdefault("properties", {})
        props["models"] = model_prop(TE_NAME, TE_URL, "text_encoders")
    elif node_type == "VAELoader":
        node["widgets_values"] = [VAE_NAME]
        props = node.setdefault("properties", {})
        props["models"] = model_prop(VAE_NAME, VAE_URL, "vae")
    elif node_type == "LoraLoaderModelOnly":
        node["widgets_values"] = [LORA_NAME, 1]
        props = node.setdefault("properties", {})
        props["models"] = model_prop(LORA_NAME, LORA_URL, "loras")
    elif node_type == "PrimitiveBoolean" and "4steps" in str(node.get("title", "")):
        node["widgets_values"] = [True]
    elif node_type == "SaveImage":
        node["widgets_values"] = ["qwen_image_edit_2511/"]


def main() -> None:
    data = replace_strings(json.loads(WORKFLOW.read_text(encoding="utf-8")))
    for node in walk_nodes(data):
        patch_node(node)
    WORKFLOW.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {WORKFLOW.relative_to(REPO)}")


if __name__ == "__main__":
    main()
