#!/usr/bin/env python3
"""Generate Flux 2 Klein 4B workflow JSON from 9B templates."""
from pathlib import Path


def klein_4b_t2i(text: str) -> str:
    reps = [
        ("flux-2-klein-9b-fp8", "flux-2-klein-4b-fp8"),
        ("FLUX.2-klein-9b-fp8", "FLUX.2-klein-4b-fp8"),
        ("qwen_3_8b_fp8mixed", "qwen_3_4b"),
        ("flux2-klein-9B", "flux2-klein-4B"),
        ("FLUX.2 9B Klein", "FLUX.2 4B Klein"),
        ("Flux.2 Klein 9B", "Flux.2 Klein 4B"),
        ("9B Klein", "4B Klein"),
        ("9b Klein", "4b Klein"),
        ("9B Distilled", "4B Distilled"),
    ]
    for old, new in reps:
        text = text.replace(old, new)
    return text


def klein_4b_i2i(text: str) -> str:
    text = klein_4b_t2i(text)
    reps = [
        ("full_encoder_small_decoder.safetensors", "flux2-vae.safetensors"),
        (
            "https://huggingface.co/black-forest-labs/FLUX.2-small-decoder/resolve/main/full_encoder_small_decoder.safetensors",
            "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors",
        ),
    ]
    for old, new in reps:
        text = text.replace(old, new)
    return text


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "workflows" / "flux2"
    t2i_src = root / "klein-9b-t2i.json"
    i2i_src = root / "klein-9b-edit.json"
    t2i_out = root / "klein-4b-t2i.json"
    i2i_out = root / "klein-4b-edit.json"
    t2i_out.write_text(klein_4b_t2i(t2i_src.read_text(encoding="utf-8")), encoding="utf-8")
    i2i_out.write_text(klein_4b_i2i(i2i_src.read_text(encoding="utf-8")), encoding="utf-8")
    t2i = t2i_out.read_text(encoding="utf-8")
    i2i = i2i_out.read_text(encoding="utf-8")
    assert "flux-2-klein-4b-fp8" in t2i and "qwen_3_4b" in t2i
    assert "flux-2-klein-9b" not in t2i
    assert "flux-2-klein-4b-fp8" in i2i and "flux2-vae.safetensors" in i2i
    assert "full_encoder_small_decoder" not in i2i
    print(f"[OK] {t2i_out.name} ({t2i_out.stat().st_size} bytes)")
    print(f"[OK] {i2i_out.name} ({i2i_out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
