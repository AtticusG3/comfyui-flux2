#!/usr/bin/env python3
"""Prune GHCR container versions and GitHub releases for comfyui-flux2.

Retention policy (default):
  - Keep image tags: latest, main, and the highest semver per major (cu130 / no CUDA suffix).
  - Delete GHCR versions tagged *-cu126 or *-cu128 (legacy matrix builds).
  - Delete other GHCR versions with downloadsTotalCount < min_downloads (default: 2).
  - Delete GitHub releases whose tag is not in the keep set (highest patch per major + latest).

Requires: gh CLI, token with read:packages and delete:packages (and repo for releases).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

SEMVER_RE = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:-(?P<suffix>cu\d+))?$",
    re.IGNORECASE,
)
LEGACY_CUDA_RE = re.compile(r"-cu126$|-cu128$", re.IGNORECASE)
PROTECTED_FLOATING = frozenset({"latest", "main"})


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    suffix: str | None = None

    @classmethod
    def parse_tag(cls, tag: str) -> SemVer | None:
        m = SEMVER_RE.match(tag.strip())
        if not m:
            return None
        suffix = m.group("suffix")
        if suffix and suffix.lower() not in ("cu130",):
            return None
        return cls(
            int(m.group("major")),
            int(m.group("minor")),
            int(m.group("patch")),
            suffix.lower() if suffix else None,
        )

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def tag_v(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"


def run_gh(args: list[str], *, check: bool = True) -> str:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout or "gh failed\n")
        raise SystemExit(proc.returncode)
    return proc.stdout


def gh_json(args: list[str]) -> Any:
    out = run_gh(args)
    if not out.strip():
        return None
    return json.loads(out)


def repo_owner_name(owner: str | None, repo: str | None) -> tuple[str, str]:
    if owner and repo:
        return owner, repo
    data = gh_json(["repo", "view", "--json", "owner,name"])
    return data["owner"]["login"], data["name"]


def protected_semver_tags(all_tags: list[str]) -> set[str]:
    """Highest patch per major among cu130 / unsuffixed semver tags."""
    by_major: dict[int, SemVer] = {}
    for tag in all_tags:
        sv = SemVer.parse_tag(tag)
        if sv is None:
            continue
        cur = by_major.get(sv.major)
        if cur is None or sv.as_tuple() > cur.as_tuple():
            by_major[sv.major] = sv
    return {sv.tag_v() for sv in by_major.values()}


def is_legacy_cuda_tag(tag: str) -> bool:
    return bool(LEGACY_CUDA_RE.search(tag))


def tag_is_protected(tag: str, protected_semver: set[str]) -> bool:
    if tag in PROTECTED_FLOATING:
        return True
    if is_legacy_cuda_tag(tag):
        return False
    sv = SemVer.parse_tag(tag)
    if sv and sv.tag_v() in protected_semver:
        return True
    bare = tag.lstrip("v")
    if bare in {p.lstrip("v") for p in protected_semver}:
        return True
    return False


def list_ghcr_versions(owner: str, package: str) -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    page = 1
    while True:
        chunk = gh_json(
            [
                "api",
                f"/users/{owner}/packages/container/{package}/versions",
                "-f",
                f"per_page=100",
                "-f",
                f"page={page}",
            ]
        )
        if not chunk:
            break
        versions.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return versions


def fetch_download_counts(owner: str, repo: str) -> dict[str, int]:
    query = """
    query($owner: String!, $name: String!, $after: String) {
      repository(owner: $owner, name: $name) {
        packages(packageType: DOCKER, first: 10) {
          nodes {
            versions(first: 100, after: $after) {
              pageInfo { hasNextPage endCursor }
              nodes {
                id
                statistics { downloadsTotalCount }
              }
            }
          }
        }
      }
    }
    """
    counts: dict[str, int] = {}
    after: str | None = None
    while True:
        args = [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"owner={owner}",
            "-f",
            f"name={repo}",
        ]
        if after:
            args.extend(["-f", f"after={after}"])
        data = gh_json(args)
        repo_data = data.get("data", {}).get("repository")
        if not repo_data:
            break
        for pkg in repo_data.get("packages", {}).get("nodes") or []:
            versions = pkg.get("versions") or {}
            for node in versions.get("nodes") or []:
                vid = node.get("id")
                stats = node.get("statistics") or {}
                if vid:
                    counts[vid] = int(stats.get("downloadsTotalCount") or 0)
            page_info = versions.get("pageInfo") or {}
            if page_info.get("hasNextPage"):
                after = page_info.get("endCursor")
            else:
                after = None
        if not after:
            break
    return counts


def plan_ghcr_deletions(
    versions: list[dict[str, Any]],
    download_counts: dict[str, int],
    min_downloads: int,
) -> tuple[list[dict[str, Any]], set[str]]:
    all_tags: list[str] = []
    for ver in versions:
        tags = (ver.get("metadata") or {}).get("container", {}).get("tags") or []
        all_tags.extend(tags)
    protected_semver = protected_semver_tags(all_tags)

    to_delete: list[dict[str, Any]] = []
    for ver in versions:
        vid = str(ver.get("id", ""))
        tags = (ver.get("metadata") or {}).get("container", {}).get("tags") or []
        if not tags:
            to_delete.append(ver)
            continue
        if any(is_legacy_cuda_tag(t) for t in tags):
            to_delete.append(ver)
            continue
        if any(tag_is_protected(t, protected_semver) for t in tags):
            continue
        downloads = download_counts.get(vid, 0)
        if downloads < min_downloads:
            to_delete.append(ver)
    return to_delete, protected_semver


def plan_release_deletions(protected_semver: set[str]) -> list[str]:
    releases = gh_json(["release", "list", "--limit", "200", "--json", "tagName,isLatest"])
    keep: set[str] = set(protected_semver)
    for rel in releases:
        if rel.get("isLatest"):
            keep.add(rel["tagName"])
    to_delete: list[str] = []
    for rel in releases:
        tag = rel["tagName"]
        if tag in keep:
            continue
        sv = SemVer.parse_tag(tag)
        if sv is None:
            continue
        to_delete.append(tag)
    return to_delete


def delete_ghcr_version(owner: str, package: str, version_id: int) -> None:
    run_gh(
        [
            "api",
            "--method",
            "DELETE",
            f"/users/{owner}/packages/container/{package}/versions/{version_id}",
        ]
    )


def delete_release(tag: str) -> None:
    run_gh(["release", "delete", tag, "--yes", "--cleanup-tag"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", help="GitHub user/org (default: current repo owner)")
    parser.add_argument("--repo", help="Repository name (default: current repo)")
    parser.add_argument(
        "--package",
        default="comfyui-flux2",
        help="GHCR container package name (default: comfyui-flux2)",
    )
    parser.add_argument(
        "--min-downloads",
        type=int,
        default=2,
        help="Keep GHCR versions with at least this many downloads (default: 2)",
    )
    parser.add_argument("--apply", action="store_true", help="Perform deletions (default: dry run)")
    parser.add_argument("--skip-ghcr", action="store_true", help="Skip GHCR version cleanup")
    parser.add_argument("--skip-releases", action="store_true", help="Skip GitHub release cleanup")
    args = parser.parse_args()

    owner, repo = repo_owner_name(args.owner, args.repo)
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] Registry cleanup for {owner}/{repo} package={args.package}")
    print(f"[INFO] min_downloads={args.min_downloads} (delete when count < this)")

    protected_semver: set[str] = set()

    if not args.skip_ghcr:
        try:
            versions = list_ghcr_versions(owner, args.package)
        except SystemExit:
            print("[ERROR] Cannot list GHCR versions. Token needs read:packages.", file=sys.stderr)
            return 1
        try:
            downloads = fetch_download_counts(owner, repo)
        except SystemExit:
            print("[WARN] Cannot read download counts; only legacy CUDA tags will be pruned.", file=sys.stderr)
            downloads = {}
        to_delete, protected_semver = plan_ghcr_deletions(
            versions, downloads, args.min_downloads
        )
        print(f"[INFO] Keeping semver majors (highest patch): {', '.join(sorted(protected_semver)) or '(none)'}")
        print(f"[INFO] GHCR versions to delete: {len(to_delete)} / {len(versions)}")
        for ver in to_delete:
            tags = (ver.get("metadata") or {}).get("container", {}).get("tags") or []
            vid = ver.get("id")
            dls = downloads.get(str(vid), "?")
            print(f"  - id={vid} tags={tags} downloads={dls}")
            if args.apply and vid is not None:
                delete_ghcr_version(owner, args.package, int(vid))
                print(f"    [OK] deleted GHCR version {vid}")

    if not args.skip_releases:
        if not protected_semver:
            all_tags = []
            try:
                versions = list_ghcr_versions(owner, args.package)
                for ver in versions:
                    all_tags.extend(
                        (ver.get("metadata") or {}).get("container", {}).get("tags") or []
                    )
            except SystemExit:
                pass
            protected_semver = protected_semver_tags(all_tags)
        release_tags = plan_release_deletions(protected_semver)
        print(f"[INFO] GitHub releases to delete: {len(release_tags)}")
        for tag in release_tags:
            print(f"  - release {tag}")
            if args.apply:
                delete_release(tag)
                print(f"    [OK] deleted release {tag}")

    if not args.apply:
        print("[INFO] Dry run only. Re-run with --apply to delete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
