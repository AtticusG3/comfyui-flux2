"""Shared ComfyUI workflow link list parsing helpers."""
from __future__ import annotations

from typing import Any


def links_kind(links: list[Any]) -> str | None:
    if not links:
        return "tuple"
    first = links[0]
    if isinstance(first, list):
        return "tuple"
    if isinstance(first, dict):
        return "object"
    return None


def link_fields(link: Any, kind: str) -> tuple[int | None, Any, Any]:
    """Return (link_id, origin_node_id, target_node_id) for tuple or object links."""
    if kind == "tuple":
        if not isinstance(link, list) or len(link) < 5:
            return None, None, None
        return link[0], link[1], link[3]
    if not isinstance(link, dict):
        return None, None, None
    return link.get("id"), link.get("origin_id"), link.get("target_id")
