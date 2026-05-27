#!/usr/bin/env python3
"""Apply pack example prompts from SCENES registry into bundled workflow JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lib.workflow_prompts import apply_prompts

SDXL_NEG = (
    "worst quality, low quality, normal quality, jpeg artifacts, blurry, "
    "watermark, signature, text overlay, deformed, bad anatomy, extra fingers, "
    "mutated hands, disfigured, (poorly drawn hands:1.3), bad proportions, "
    "cropped, out of frame, overexposed, underexposed"
)
VIDEO_NEG = (
    "blurry, low quality, watermark, text, distorted motion, flickering, "
    "inconsistent lighting, morphing faces, extra limbs"
)
ANIME_NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, worst quality, low quality, normal quality, jpeg "
    "artifacts, signature, watermark, username, blurry, artist name"
)

# Portrait + specific car + famous location; anime packs name notable female characters.
SCENES: dict[str, tuple[str, str]] = {
    "workflows/flux2/klein-t2i.json": (
        "Portrait of Asuka Langley in red plugsuit cosplay leaning on a Nissan Skyline GT-R R34 "
        "V-Spec II at Shibuya Scramble Crossing at night, neon reflections on wet asphalt, "
        "cinematic automotive photography, 85mm lens",
        "",
    ),
    "workflows/flux2/klein-edit.json": (
        "Change the Skyline to a midnight purple widebody R34 with Varis aero and larger rear wing, "
        "keep Asuka cosplay pose and Shibuya night background unchanged",
        "",
    ),
    "workflows/sdxl-lightning/sdxl-lightning-t2i.json": (
        "Portrait of a woman styled as Zero Two in white and red racing suit beside a Honda NSX-R "
        "at the Nurburgring Nordschleife carousel, overcast sky, telephoto motorsport photography, "
        "motion blur on background crowd",
        SDXL_NEG,
    ),
    "workflows/sdxl-lightning/sdxl-lightning-hires.json": (
        "Portrait of a woman styled as Makima in elegant black coat beside a Lamborghini Huracan STO "
        "on the Amalfi Coast cliff road at golden hour, Mediterranean sea below, photorealistic hires "
        "detail, medium-format texture",
        SDXL_NEG,
    ),
    "workflows/flux1-krea/flux-krea-t2i.json": (
        "Portrait of Saber in casual summer dress beside a Kawasaki Z900RS cafe racer at Senso-ji Temple "
        "Asakusa main gate, late autumn maples, Kodak Portra 400 film look, soft halation",
        "",
    ),
    "workflows/newbie-image/newbie-t2i-low.json": (
        "<subject>Hatsune Miku in black and gold racing queen outfit beside a Nissan Silvia S15 Spec-R</subject> "
        "<background>Fuji Speedway paddock, Mount Fuji in distance, Super GT atmosphere</background> "
        "<style>high-detail anime illustration, vibrant cel-shading</style> "
        "<quality>masterpiece, best quality, sharp</quality>",
        ANIME_NEG,
    ),
    "workflows/newbie-image/newbie-t2i-high.json": (
        "<subject>Rem from Re:Zero in maid outfit beside a Subaru WRX STI WRB at Akihabara night street</subject> "
        "<background>neon signs, light rain, crowded sidewalk</background> "
        "<style>detailed anime illustration, cinematic rim light</style> "
        "<quality>masterpiece, best quality</quality>",
        ANIME_NEG,
    ),
    "workflows/ovis-image/ovis-t2i.json": (
        "Event poster: Saber in armor beside a Mazda RX-7 FD at Ebisu Circuit drift stadium, bold title "
        "DRIFT MATSURI 2025, Japanese subtitle, high contrast print design",
        ANIME_NEG,
    ),
    "workflows/wan-2-2/wan22-5b-t2v.json": (
        "Toyota AE86 Trueno driven by a young woman with teal twin-tails on Gunma mountain touge at dawn, "
        "cedar forest, tyre smoke in sunrise, low tracking shot, smooth cinematic motion",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-5b-i2v.json": (
        "Animate: driver hands on AE86 steering wheel, tachometer climbing, Gunma hairpin visible through "
        "windscreen, subtle camera shake, consistent interior detail",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-14b-t2v.json": (
        "JGTC grid start at Suzuka Circuit, Castrol Tom's Supra and Nismo GT-R, female race engineer in "
        "foreground, packed grandstands, broadcast camera pan, consistent vehicle motion",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-14b-i2v.json": (
        "Animate: female driver in white helmet beside a Toyota Supra MK4 at Fuji Speedway raises visor and "
        "waves, steam from hood, mechanics approach, confetti falls, natural crowd motion",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-14b-inpaint.json": (
        "Transform the foreground car paint to black-and-gold Keiichi Tsuchiya Levin livery, kanji door text "
        "appears smoothly, all other scene elements unchanged, cinematic motion",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-14b-camera.json": (
        "Initial D style chase on Hakone touge at night, RX-7 Spirit R and Lancer Evo IX, camera moves from "
        "roof POV to roadside tracking to aerial reveal, vending machine glow, coherent motion",
        VIDEO_NEG,
    ),
    "workflows/ace-step/ace-step-t2m.json": (
        "Japanese city pop, 1980s Shibuya-kei, driving synth bass, Rhodes piano, brushed drums, female vocal "
        "hooks, coastal night drive mood, 108 BPM, F major",
        "",
    ),
    "workflows/hunyuan-3d/hunyuan3d-i2-3d.json": (
        "Highly detailed 3D model of a Nissan Silvia S15 Spec-R, Brilliant Blue pearl paint, TE37 wheels, "
        "clean game-ready topology, studio three-quarter view",
        "",
    ),
    "workflows/z-anime/z-anime-t2i.json": (
        "Saber from Fate in armor beside a Mazda RX-7 FD at Chureito Pagoda with Mount Fuji behind, "
        "sunset sky, detailed anime illustration, cinematic composition",
        ANIME_NEG,
    ),
    "workflows/z-image-turbo/z-turbo-t2i.json": (
        "Portrait of a woman styled as Faye Valentine beside a Toyota GR Yaris Circuit Edition on a Hakone "
        "hairpin at night, light rain, guardrail reflections, 35mm photoreal",
        "",
    ),
    "workflows/z-image-turbo/z-base-t2i.json": (
        "Studio portrait of an Asuka Langley figure beside a Porsche 911 GT3 RS model on grey sweep, "
        "commercial product photography, sharp focus",
        "",
    ),
    "workflows/ernie-image/ernie-sft-t2i.json": (
        "Watercolor illustration of Rem in maid outfit beside a Nissan Fairlady Z at Kyoto Fushimi Inari "
        "torii tunnel, soft edges, muted indigo and vermillion palette",
        "",
    ),
    "workflows/ernie-image/ernie-turbo-t2i.json": (
        "Bold vector sticker of Hatsune Miku beside a Nissan GT-R R35 at Tokyo Tower base, flat colors, "
        "thick white outline, print-ready",
        "",
    ),
    "workflows/firered-image-edit/firered-edit.json": (
        "Change the jacket to a bright indigo technical shell with reflective piping, keep portrait pose "
        "and Monaco harbor background with Ferrari 488 in frame",
        "",
    ),
    "workflows/qwen-image-edit-2511/qwen-edit-2511.json": (
        "Change the outfit to a red racing suit with white stripes, keep portrait pose beside the BMW M3 "
        "at Monaco harbor background unchanged",
        "",
    ),
    "workflows/realvisxl/realvisxl-lightning-t2i.json": (
        "Portrait of Misato Katsuragi-inspired woman in red coat beside a Nissan Skyline GT-R R32 at "
        "Tokyo Rainbow Bridge at night, gritty urban photoreal",
        SDXL_NEG,
    ),
    "workflows/realvisxl/realvisxl-v5-hires.json": (
        "Portrait styled as Yor Forger in black dress beside an Aston Martin DB5 at Lake Como waterfront, "
        "villa terraces behind, photorealistic hires pass",
        SDXL_NEG,
    ),
    "workflows/hidream-o1/hidream-o1-example.json": (
        "Portrait of Saber in red coat beside a Mercedes-AMG GT at Piazza San Marco Venice at blue hour, "
        "editorial fashion photography",
        "",
    ),
    "workflows/hunyuan-video/hunyuan-video-guide.json": (
        "A cat walking on a beach at sunset, gentle waves, cinematic motion",
        VIDEO_NEG,
    ),
    "workflows/sdxl-editing/sdxl-img2img.json": (
        "Replace the car with a Mitsubishi Lancer Evolution VIII in Evo Blue Pearl at the same lighting "
        "and camera angle",
        SDXL_NEG,
    ),
    "workflows/sdxl-editing/sdxl-inpaint.json": (
        "Fill the masked region with matching asphalt texture and lane markings, keep surrounding scene",
        SDXL_NEG,
    ),
    "workflows/sdxl-editing/sdxl-outpaint.json": (
        "Extend the scene with more Monaco harbor waterfront and yachts, consistent perspective and lighting",
        SDXL_NEG,
    ),
}


def update_file(path: Path, positive: str, negative: str) -> tuple[bool, int, int, int]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    changed, pos_count, neg_count, fallback_count = apply_prompts(
        doc, positive, negative, repo_root=REPO_ROOT, embed_subgraphs=True
    )
    if changed:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rel = path.as_posix()
    print(f"[OK] {rel}: positive prompt set ({len(positive)} chars), negative prompt set")
    return changed, pos_count, neg_count, fallback_count


def pack_name(rel_path: str) -> str:
    if "workflow-flux2-klein" in rel_path or "flux2/" in rel_path:
        return "flux2"
    if "sdxl-lightning/" in rel_path:
        return "sdxl-lightning"
    if "flux1-krea/" in rel_path:
        return "flux1-krea"
    if "newbie-image/" in rel_path:
        return "newbie-image"
    if "ovis-image/" in rel_path:
        return "ovis-image"
    if "wan-2-2/" in rel_path:
        return "wan-2-2"
    if "ace-step/" in rel_path:
        return "ace-step"
    if "hunyuan-3d/" in rel_path:
        return "hunyuan-3d"
    if "z-anime/" in rel_path:
        return "z-image-anime"
    if "ernie-image/" in rel_path:
        return "ernie-image"
    if "firered-image-edit/" in rel_path:
        return "firered-image-edit"
    if "qwen-image-edit" in rel_path:
        return "qwen-image-edit-2511"
    return "other"


def safe_console(text: str) -> str:
    return text.encode("cp1252", errors="replace").decode("cp1252")


def main() -> None:
    root = Path("workflows")
    files = sorted(
        p.as_posix()
        for p in root.rglob("*.json")
        if "/_templates/" not in p.as_posix()
        and p.name.endswith(".json")
        and p.name[0].islower()
    )
    missing = [f for f in files if f not in SCENES]
    if missing:
        raise RuntimeError(f"Scene mapping missing for files: {missing}")

    verification: dict[str, dict] = {}
    for rel in files:
        pos, neg = SCENES[rel]
        changed, pos_count, neg_count, fallback_count = update_file(Path(rel), pos, neg)
        pack = pack_name(rel)
        if pack not in verification:
            verification[pack] = {
                "file": rel,
                "positive": pos,
                "negative": neg,
                "changed": changed,
                "pos_count": pos_count,
                "neg_count": neg_count,
                "fallback_count": fallback_count,
            }

    print("\n[VERIFY] One workflow per pack:")
    for pack in sorted(verification):
        info = verification[pack]
        print(f"  pack={pack} file={info['file']}")
        print(f"    positive: {safe_console(info['positive'])}")
        neg = info["negative"] if info["negative"] else "<empty>"
        print(f"    negative: {safe_console(neg)}")
        print(
            f"    counts: changed={info['changed']}, pos_nodes={info['pos_count']}, "
            f"neg_nodes={info['neg_count']}, fallback_nodes={info['fallback_count']}"
        )


if __name__ == "__main__":
    main()
