#!/usr/bin/env python3
"""Install a matching nunchaku-ai backend wheel for the current torch/Python stack."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

RELEASES_API = "https://api.github.com/repos/nunchaku-ai/nunchaku/releases/latest"


def _torch_major_minor() -> str:
    import torch

    version = torch.__version__.split("+", 1)[0]
    parts = version.split(".")
    if len(parts) < 2:
        raise RuntimeError(f"unexpected torch version: {torch.__version__}")
    return f"{parts[0]}.{parts[1]}"


def _python_tag() -> str:
    major, minor = sys.version_info[:2]
    return f"cp{major}{minor}"


def _fetch_assets() -> list[dict[str, str]]:
    request = urllib.request.Request(
        RELEASES_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "comfyui-flux2-entrypoint"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    return [
        {"name": asset["name"], "url": asset["browser_download_url"]}
        for asset in payload.get("assets", [])
        if asset.get("name", "").endswith(".whl")
    ]


def _pick_wheel(assets: list[dict[str, str]], torch_mm: str, py_tag: str) -> dict[str, str] | None:
    linux_assets = [asset for asset in assets if "linux_x86_64" in asset["name"] and py_tag in asset["name"]]
    if not linux_assets:
        return None

    cuda_tags = ("cu13.0", "cu12.8")
    torch_tags = [torch_mm]
    parts = torch_mm.split(".")
    if len(parts) == 2:
        major, minor = int(parts[0]), int(parts[1])
        if minor > 0:
            torch_tags.append(f"{major}.{minor - 1}")
        torch_tags.append(f"{major}.{minor + 1}")

    pattern = re.compile(
        r"^nunchaku-[^+]+\+(?P<cuda>cu[\d.]+)torch(?P<torch>[\d.]+)-"
        + re.escape(py_tag)
        + r"-"
        + re.escape(py_tag)
        + r"-linux_x86_64\.whl$"
    )

    ranked: list[tuple[int, int, dict[str, str]]] = []
    for asset in linux_assets:
        match = pattern.match(asset["name"])
        if not match:
            continue
        cuda = match.group("cuda")
        torch_tag = match.group("torch")
        cuda_rank = cuda_tags.index(cuda) if cuda in cuda_tags else len(cuda_tags)
        torch_rank = torch_tags.index(torch_tag) if torch_tag in torch_tags else len(torch_tags) + 10
        ranked.append((cuda_rank, torch_rank, asset))

    if not ranked:
        return None

    ranked.sort(key=lambda item: (item[0], item[1]))
    return ranked[0][2]


def main() -> int:
    try:
        import nunchaku  # noqa: F401
    except ImportError:
        pass
    else:
        print("[OK] nunchaku already importable")
        return 0

    torch_mm = _torch_major_minor()
    py_tag = _python_tag()
    print(f"[INFO] Selecting nunchaku wheel for torch {torch_mm} and {py_tag}...")

    try:
        assets = _fetch_assets()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"[WARN] Failed to query nunchaku releases: {exc}")
        return 1

    wheel = _pick_wheel(assets, torch_mm, py_tag)
    if wheel is None:
        print(
            "[WARN] No compatible nunchaku wheel found for this torch/Python stack. "
            "Install manually from https://github.com/nunchaku-ai/nunchaku/releases"
        )
        return 1

    print(f"[INFO] Installing nunchaku wheel: {wheel['name']}")
    result = subprocess.run(["uv", "pip", "install", wheel["url"]], check=False)
    if result.returncode != 0:
        print("[WARN] nunchaku wheel install failed")
        return result.returncode

    try:
        import nunchaku  # noqa: F401
    except ImportError:
        print("[WARN] nunchaku wheel installed but import still failing")
        return 1

    print("[OK] nunchaku backend installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
