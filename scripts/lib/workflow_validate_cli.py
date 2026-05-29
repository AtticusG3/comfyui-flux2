"""Shared CLI helpers for workflow validators."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable


def emit(path: str | Path, gate: str, ok: bool, msg: str = "") -> None:
    line = f"{path}  {gate}  {'PASS' if ok else 'FAIL'}"
    if msg:
        line += f"  {msg}"
    sys.stdout.write(line + "\n")


def expand_paths(
    raw_paths: list[str],
    repo_root: Path,
    *,
    skip_templates: bool = True,
) -> list[Path]:
    output: list[Path] = []
    for raw in raw_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = repo_root / path
        if path.is_dir():
            candidates = sorted(path.rglob("*.json"))
        else:
            candidates = [path]
        for candidate in candidates:
            if skip_templates and "_templates" in candidate.parts:
                continue
            output.append(candidate)
    return output


def to_rel_paths(paths: Iterable[Path], repo_root: Path) -> list[str]:
    rel_paths: list[str] = []
    for path in paths:
        try:
            rel_paths.append(str(path.relative_to(repo_root)))
        except ValueError:
            rel_paths.append(str(path))
    return rel_paths


def run_validator_script(
    *,
    script_path: Path,
    repo_root: Path,
    rel_paths: list[str],
    gate_label: str,
    extra_args: list[str] | None = None,
) -> bool:
    if not script_path.is_file():
        emit("workflows/", gate_label, False, f"{gate_label} script missing")
        return False
    command = [sys.executable, str(script_path), *(extra_args or []), *rel_paths]
    proc = subprocess.run(
        command,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        for line in proc.stdout.rstrip().splitlines():
            sys.stdout.write(f"{line}\n")
    if proc.stderr:
        for line in proc.stderr.rstrip().splitlines():
            sys.stdout.write(f"[{gate_label}][stderr] {line}\n")
    ok = proc.returncode == 0
    if not ok and not proc.stdout:
        emit("workflows/", gate_label, False, f"exit {proc.returncode}")
    return ok
