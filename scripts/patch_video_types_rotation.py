#!/usr/bin/env python3
"""Patch ComfyUI video_types.py for PyAV builds without frame.rotation."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def patch_text(text: str) -> tuple[str, bool]:
    if 'getattr(frame, "rotation", None)' in text:
        return text, False

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    patched = False

    while i < len(lines):
        line = lines[i]
        if (
            not patched
            and "if frame.rotation != 0:" in line
            and i + 2 < len(lines)
            and "frame.rotation // 90" in lines[i + 1]
            and "np.rot90" in lines[i + 2]
        ):
            indent = line[: len(line) - len(line.lstrip())]
            inner = indent + "    "
            out.extend(
                [
                    f'{indent}rotation = getattr(frame, "rotation", None)\n',
                    f"{indent}if rotation is None:\n",
                    f'{inner}md = getattr(frame, "metadata", None)\n',
                    f'{inner}rotation = int(md.get("rotate", 0)) if isinstance(md, dict) else 0\n',
                    f"{indent}if rotation != 0:\n",
                    f"{inner}k = int(round(float(rotation) / 90.0)) % 4\n",
                    f"{inner}if k:\n",
                    f"{inner}    img = np.rot90(img, k=k, axes=(0, 1)).copy()\n",
                ]
            )
            i += 3
            patched = True
            continue

        out.append(line)
        i += 1

    return "".join(out), patched


def main() -> int:
    comfy_dir = Path(os.environ.get("COMFYUI_DIR", "/app/ComfyUI"))
    path = comfy_dir / "comfy_api" / "latest" / "_input_impl" / "video_types.py"
    if not path.is_file():
        print(f"[WARN] {path} not found; skipping rotation patch.")
        return 0

    text = path.read_text(encoding="utf-8")
    patched_text, changed = patch_text(text)
    if not changed:
        if 'getattr(frame, "rotation", None)' in text:
            print("[INFO] video_types.py rotation fallback already present.")
        else:
            print("[ERROR] video_types.py rotation block not found.", file=sys.stderr)
            return 1
        return 0

    path.write_text(patched_text, encoding="utf-8")
    print("[OK] Patched video_types.py rotation fallback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
