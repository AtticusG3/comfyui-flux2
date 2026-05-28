#!/usr/bin/env python3
"""Semantic checks for bundled ComfyUI pack workflows (defaults + example prompts)."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lib.workflow_prompts import extract_prompts as extract_workflow_prompts
from lib.workflow_prompts import iter_graphs as iter_workflow_graphs
WORKFLOWS_DIR = REPO_ROOT / "workflows"
PROMPTS_SCRIPT = REPO_ROOT / "scripts" / "update_workflow_prompts.py"

PLACEHOLDER_RE = re.compile(
    r"^(text|prompt|positive|negative|description|\.\.\.|test|example)\s*$",
    re.I,
)

PEOPLE_TERMS = (
    "portrait",
    "person",
    "people",
    "woman",
    "man",
    "girl",
    "boy",
    "driver",
    "pilot",
    "attendant",
    "figure",
    "figures",
    "crowd",
    "marshal",
    "mechanic",
    "crew",
    "tourist",
    "silhouette",
    "subject",
    "asuka",
    "rei",
    "miku",
    "rem",
    "saber",
    "zero two",
    "faye",
    "makima",
    "yor",
    "misato",
    "cosplay",
    "anime",
)

VEHICLE_TERMS = (
    "car",
    "vehicle",
    "automobile",
    "supra",
    "skyline",
    "nissan",
    "toyota",
    "honda",
    "mazda",
    "mitsubishi",
    "subaru",
    "bmw",
    "mercedes",
    "porsche",
    "ferrari",
    "lamborghini",
    "motorcycle",
    "bike",
    "ae86",
    "nsx",
    "evo",
    "gtr",
    "rx-7",
    "silvia",
    "yaris",
    "helmet",
    "shinkansen",
    "train",
)

SCENIC_TERMS = (
    "scenic",
    "landscape",
    "mountain",
    "coast",
    "beach",
    "sunset",
    "sunrise",
    "hairpin",
    "road",
    "street",
    "circuit",
    "paddock",
    "warehouse",
    "station",
    "crossing",
    "harbour",
    "harbor",
    "bay",
    "valley",
    "forest",
    "rain",
    "night",
    "dusk",
    "dawn",
    "skyline view",
    "city",
    "urban",
    "rural",
    "countryside",
    "location",
    "environment",
    "background",
)

EDIT_VERBS = (
    "change",
    "replace",
    "turn",
    "swap",
    "remove",
    "add",
    "make",
    "transform",
    "edit",
    "keep",
    "fill",
    "extend",
    "animate",
    "mask",
)


@dataclass(frozen=True)
class PackProfile:
    kind: str
    prompt_mode: str
    lightning: bool = False
    lightning_steps: int = 4
    full_steps: tuple[int, ...] = (20, 40)
    cfg_lightning: tuple[float, float] = (3.5, 4.5)
    cfg_full: tuple[float, float] = (1.0, 5.0)
    expect_lora_substr: str | None = None
    expect_turbo_default: bool | None = None
    require_empty_flux2_latent: bool = False
    skip_defaults: bool = False


PACK_PROFILES: dict[str, PackProfile] = {
    "qwen-image-edit-2511": PackProfile(
        kind="edit",
        prompt_mode="edit_instruction",
        lightning=True,
        lightning_steps=4,
        full_steps=(20, 40),
        expect_lora_substr="Lightning-4steps",
        expect_turbo_default=True,
    ),
    "firered-image-edit": PackProfile(
        kind="edit",
        prompt_mode="edit_instruction",
        lightning=True,
        lightning_steps=8,
        full_steps=(8, 30),
        expect_lora_substr="Lightning",
    ),
    "sdxl-lightning": PackProfile(
        kind="t2i",
        prompt_mode="portrait_car_scenic",
        lightning=True,
        lightning_steps=4,
        full_steps=(4, 8),
        cfg_lightning=(1.0, 2.5),
    ),
    "flux2": PackProfile(
        kind="t2i",
        prompt_mode="portrait_car_scenic",
        require_empty_flux2_latent=True,
    ),
    "klein-distilled": PackProfile(
        kind="t2i",
        prompt_mode="portrait_car_scenic",
        require_empty_flux2_latent=True,
    ),
    "flux1-krea": PackProfile(kind="t2i", prompt_mode="portrait_car_scenic"),
    "realvisxl": PackProfile(kind="t2i", prompt_mode="portrait_car_scenic"),
    "z-image-turbo": PackProfile(kind="t2i", prompt_mode="portrait_car_scenic"),
    "z-image-base": PackProfile(kind="t2i", prompt_mode="product_or_studio"),
    "z-image-anime": PackProfile(kind="t2i", prompt_mode="anime_portrait"),
    "z-anime": PackProfile(kind="t2i", prompt_mode="anime_portrait"),
    "newbie-image": PackProfile(kind="t2i", prompt_mode="anime_scene"),
    "ovis-image": PackProfile(kind="t2i", prompt_mode="poster_or_graphic"),
    "ernie-image": PackProfile(kind="t2i", prompt_mode="stylized"),
    "wan-2-2": PackProfile(kind="video", prompt_mode="video_motion"),
    "hunyuan-video": PackProfile(
        kind="guide", prompt_mode="skip", skip_defaults=True
    ),
    "hunyuan-3d": PackProfile(kind="3d", prompt_mode="object"),
    "ace-step": PackProfile(kind="audio", prompt_mode="audio"),
    "sdxl-editing": PackProfile(kind="edit", prompt_mode="edit_instruction"),
    "hidream-o1": PackProfile(kind="t2i", prompt_mode="portrait_car_scenic"),
}

# Per-file overrides (path suffix after workflows/).
WORKFLOW_PROFILE_OVERRIDES: dict[str, PackProfile] = {
    "sdxl-lightning/sdxl-lightning-hires.json": PackProfile(
        kind="t2i",
        prompt_mode="portrait_car_scenic",
        lightning=False,
        full_steps=(5, 18, 32),
    ),
}


def load_scenes() -> dict[str, tuple[str, str]]:
    if not PROMPTS_SCRIPT.is_file():
        return {}
    spec = importlib.util.spec_from_file_location("update_workflow_prompts", PROMPTS_SCRIPT)
    if spec is None or spec.loader is None:
        return {}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    scenes = getattr(mod, "SCENES", {})
    return scenes if isinstance(scenes, dict) else {}


def extract_prompts(doc: dict[str, Any]) -> list[str]:
    return extract_workflow_prompts(doc, REPO_ROOT)


def extract_step_cfg_primitives(doc: dict[str, Any]) -> tuple[list[int], list[float]]:
    steps: list[int] = []
    cfgs: list[float] = []
    for graph in iter_workflow_graphs(doc, REPO_ROOT):
        for node in graph.get("nodes", []):
            if not isinstance(node, dict):
                continue
            title = str(node.get("title", "")).lower()
            values = node.get("widgets_values")
            if node.get("type") == "PrimitiveInt" and "step" in title:
                if isinstance(values, list) and values and isinstance(values[0], int):
                    steps.append(values[0])
            if node.get("type") == "PrimitiveFloat" and title == "cfg":
                if isinstance(values, list) and values and isinstance(values[0], (int, float)):
                    cfgs.append(float(values[0]))
            if node.get("type") == "KSampler" and isinstance(values, list) and len(values) >= 4:
                if isinstance(values[2], int):
                    steps.append(values[2])
                if isinstance(values[3], (int, float)):
                    cfgs.append(float(values[3]))
    return steps, cfgs


def extract_lora_names(doc: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for graph in iter_workflow_graphs(doc, REPO_ROOT):
        for node in graph.get("nodes", []):
            if not isinstance(node, dict):
                continue
            if node.get("type") != "LoraLoaderModelOnly":
                continue
            values = node.get("widgets_values")
            if isinstance(values, list) and values and isinstance(values[0], str):
                names.append(values[0])
    return names


def extract_turbo_defaults(doc: dict[str, Any]) -> list[bool]:
    flags: list[bool] = []
    for graph in iter_workflow_graphs(doc, REPO_ROOT):
        for node in graph.get("nodes", []):
            if not isinstance(node, dict):
                continue
            title = str(node.get("title", "")).lower()
            if node.get("type") != "PrimitiveBoolean":
                continue
            if "4step" in title or "turbo" in title or "lightning" in title:
                values = node.get("widgets_values")
                if isinstance(values, list) and values and isinstance(values[0], bool):
                    flags.append(values[0])
    return flags


def has_node_type(doc: dict[str, Any], node_type: str) -> bool:
    for graph in iter_workflow_graphs(doc, REPO_ROOT):
        for node in graph.get("nodes", []):
            if isinstance(node, dict) and node.get("type") == node_type:
                return True
    return False


def infer_pack(rel_posix: str) -> str | None:
    parts = Path(rel_posix).parts
    if len(parts) >= 2 and parts[0] == "workflows":
        return parts[1]
    return None


def profile_for_workflow(rel_posix: str) -> PackProfile | None:
    key = rel_posix.replace("\\", "/")
    if key.startswith("workflows/"):
        key = key[len("workflows/") :]
    if key in WORKFLOW_PROFILE_OVERRIDES:
        return WORKFLOW_PROFILE_OVERRIDES[key]
    pack = infer_pack(rel_posix)
    return PACK_PROFILES.get(pack) if pack else None


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def score_portrait_car_scenic(prompt: str) -> tuple[int, list[str]]:
    missing: list[str] = []
    score = 0
    if has_any(prompt, PEOPLE_TERMS):
        score += 1
    else:
        missing.append("people/portrait")
    if has_any(prompt, VEHICLE_TERMS):
        score += 1
    else:
        missing.append("car/vehicle")
    if has_any(prompt, SCENIC_TERMS):
        score += 1
    else:
        missing.append("scenic location")
    return score, missing


def check_prompt_quality(prompt: str, profile: PackProfile) -> list[str]:
    issues: list[str] = []
    text = prompt.strip()
    if not text:
        return ["prompt is empty"]
    if len(text) < 24:
        issues.append(f"prompt too short ({len(text)} chars)")
    if PLACEHOLDER_RE.match(text):
        issues.append("prompt looks like a placeholder")

    mode = profile.prompt_mode
    if mode == "skip":
        return issues
    if mode == "edit_instruction":
        if not has_any(text, EDIT_VERBS):
            issues.append("edit workflow prompt should use an edit instruction (change/replace/keep/...)")
        return issues
    if mode == "video_motion":
        if not has_any(text, ("motion", "camera", "shot", "video", "animate", "tracking", "cinematic")):
            issues.append("video prompt should describe motion or camera")
        return issues
    if mode == "audio":
        if not has_any(text, ("bpm", "key", "vocal", "drum", "bass", "synth", "music", "style")):
            issues.append("audio prompt should describe musical style or instrumentation")
        return issues
    if mode == "anime_portrait":
        if not has_any(text, ("anime", "illustration", "cel")):
            issues.append("anime pack prompt should mention anime/illustration style")
        return issues
    if mode in ("portrait_car_scenic", "anime_scene", "stylized", "poster_or_graphic", "product_or_studio", "object"):
        score, missing = score_portrait_car_scenic(text)
        if mode == "portrait_car_scenic" and score < 2:
            issues.append(
                "prefer portrait + car + scenic location; missing: " + ", ".join(missing)
            )
        elif mode != "portrait_car_scenic" and score < 1:
            issues.append("prompt should anchor the subject or scene clearly")
    return issues


def check_defaults(doc: dict[str, Any], profile: PackProfile) -> list[str]:
    if profile.skip_defaults:
        return []

    issues: list[str] = []
    steps, cfgs = extract_step_cfg_primitives(doc)
    loras = extract_lora_names(doc)
    turbo_flags = extract_turbo_defaults(doc)

    if profile.expect_lora_substr:
        if not loras:
            issues.append(f"expected LoRA containing {profile.expect_lora_substr!r}")
        elif not any(profile.expect_lora_substr in name for name in loras):
            issues.append(
                f"LoRA filename should contain {profile.expect_lora_substr!r}; got {loras!r}"
            )

    if profile.expect_turbo_default is not None and turbo_flags:
        if turbo_flags[0] is not profile.expect_turbo_default:
            issues.append(
                f"Lightning/turbo toggle should default to {profile.expect_turbo_default}"
            )
    if profile.require_empty_flux2_latent and not has_node_type(doc, "EmptyFlux2LatentImage"):
        issues.append("expected EmptyFlux2LatentImage in workflow graph/subgraph")

    if profile.lightning:
        if profile.lightning_steps not in steps:
            issues.append(
                f"expected lightning step count {profile.lightning_steps} in graph primitives"
            )
        if not any(s in profile.full_steps for s in steps):
            issues.append(
                f"expected full-quality step option in {profile.full_steps}; got {sorted(set(steps))}"
            )
        if cfgs:
            lo, hi = profile.cfg_lightning
            if not any(lo <= c <= hi for c in cfgs):
                issues.append(f"expected lightning CFG in [{lo}, {hi}]; got {cfgs}")
    elif profile.kind == "t2i" and steps:
        if max(steps) > 50:
            issues.append(f"T2I steps look high for a distilled pack: {max(steps)}")

    return issues


def check_prompt_registry(rel_posix: str, prompts: list[str], scenes: dict[str, tuple[str, str]]) -> list[str]:
    key = rel_posix.replace("\\", "/")
    if key not in scenes:
        return []
    expected_pos, _ = scenes[key]
    if not prompts:
        return ["no positive prompt found in workflow graph"]
    if expected_pos.strip() not in prompts and prompts[0].strip() != expected_pos.strip():
        return ["workflow prompt does not match scripts/update_workflow_prompts.py SCENES entry"]
    return []


def validate_file(path: Path, scenes: dict[str, tuple[str, str]]) -> tuple[bool, list[str], list[str]]:
    rel = path.relative_to(REPO_ROOT).as_posix()
    profile = profile_for_workflow(rel)

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return False, [], [str(exc)]

    if not isinstance(doc.get("nodes"), list):
        return True, [], ["skipped: not a UI workflow graph"]

    prompts = extract_prompts(doc)
    errors: list[str] = []
    warnings: list[str] = []

    if profile is None:
        warnings.append(f"no PackProfile for pack {pack!r}; prompt/defaults checks are best-effort")
        profile = PackProfile(kind="unknown", prompt_mode="portrait_car_scenic")

    if profile.prompt_mode != "skip":
        primary = prompts[0] if prompts else ""
        if not primary and profile.prompt_mode == "object":
            warnings.append(
                "prompt-quality: image-conditioned workflow (no text prompt node; SCENES is reference only)"
            )
        elif not primary:
            errors.append("prompt-quality: prompt is empty")
        else:
            for issue in check_prompt_quality(primary, profile):
                if issue in ("prompt is empty",) or issue.startswith("prompt looks like"):
                    errors.append(f"prompt-quality: {issue}")
                else:
                    warnings.append(f"prompt-quality: {issue}")

    errors.extend(check_defaults(doc, profile))
    registry_issues = check_prompt_registry(rel, prompts, scenes)
    for issue in registry_issues:
        warnings.append(f"prompt-registry: {issue}")

    return len(errors) == 0, warnings, errors


def emit(path: str, gate: str, ok: bool, msg: str = "") -> None:
    line = f"{path}  {gate}  {'PASS' if ok else 'FAIL'}"
    if msg:
        line += f"  {msg}"
    sys.stdout.write(line + "\n")


def expand_paths(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.is_dir():
            out.extend(sorted(p.rglob("*.json")))
        else:
            out.append(p)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic validation for pack workflows.")
    parser.add_argument("paths", nargs="*", help="Workflow files or directories")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Treat prompt-quality warnings as non-fatal (defaults/registry still fail)",
    )
    args = parser.parse_args()

    targets = expand_paths(args.paths or ["workflows"])
    if not targets:
        sys.stdout.write("usage: validate_workflow_semantics.py <workflow.json> [...]\n")
        return 2

    scenes = load_scenes()
    failed = False
    for path in targets:
        if "_templates" in path.parts:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        ok, warnings, errors = validate_file(path, scenes)
        emit(rel, "semantics", ok, "; ".join(errors) if errors else "")
        for warn in warnings:
            emit(rel, "semantics-warn", True, warn)
        if not ok and not args.warn_only:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
