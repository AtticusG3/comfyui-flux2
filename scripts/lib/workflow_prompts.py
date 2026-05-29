"""Extract and apply example prompts across ComfyUI workflow graphs (incl. UUID subgraphs)."""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any, Iterator

from lib.workflow_subgraph_ports import UUID_TYPE_RE

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

def _load_embed_module():
    path = SCRIPTS_DIR / "embed_workflow_subgraphs.py"
    spec = importlib.util.spec_from_file_location("embed_workflow_subgraphs", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["embed_workflow_subgraphs"] = mod
    spec.loader.exec_module(mod)
    return mod


def link_index(links: list[Any]) -> dict[tuple[int, int], list[list[Any]]]:
    by_src: dict[tuple[int, int], list[list[Any]]] = {}
    for link in links:
        if not isinstance(link, list) or len(link) < 5:
            continue
        by_src.setdefault((link[1], link[2]), []).append(link)
    return by_src


def node_text(node: dict[str, Any]) -> str | None:
    values = node.get("widgets_values")
    if not isinstance(values, list) or not values:
        return None
    first = values[0]
    return first if isinstance(first, str) else None


def clip_encode_role(
    node: dict[str, Any],
    nodes_by_id: dict[Any, dict[str, Any]],
    by_src: dict[tuple[int, int], list[list[Any]]],
) -> str | None:
    outgoing = by_src.get((node.get("id"), 0), [])
    for link in outgoing:
        dst = nodes_by_id.get(link[3], {})
        dst_type = dst.get("type", "")
        dst_slot = link[4]
        if dst_type in ("KSampler", "KSamplerAdvanced"):
            if dst_slot == 1:
                return "positive"
            if dst_slot == 2:
                return "negative"
    title = str(node.get("title", "")).lower()
    if "negative" in title or "neg" in title:
        return "negative"
    if "positive" in title or "pos" in title:
        return "positive"
    return None


def _prompts_from_graph(graph: dict[str, Any]) -> list[str]:
    prompts: list[str] = []
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])
    if not isinstance(nodes, list):
        return prompts
    nodes_by_id = {n.get("id"): n for n in nodes if isinstance(n, dict)}
    by_src = link_index(links if isinstance(links, list) else [])

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type", "")

        if node_type == "CLIPTextEncode":
            role = clip_encode_role(node, nodes_by_id, by_src)
            text = node_text(node)
            if text and role != "negative":
                prompts.append(text.strip())
            continue

        if node_type in ("PrimitiveStringMultiline", "Text Multiline"):
            title = str(node.get("title", "")).lower()
            if "neg" in title:
                continue
            text = node_text(node)
            if text:
                prompts.append(text.strip())
            continue

        if node_type == "TextEncodeQwenImageEditPlus":
            title = str(node.get("title", "")).lower()
            if "neg" in title:
                continue
            text = node_text(node)
            if text:
                prompts.append(text.strip())
            else:
                for inp in node.get("inputs", []):
                    if not isinstance(inp, dict) or inp.get("name") != "prompt":
                        continue
                    link_id = inp.get("link")
                    if link_id is None:
                        continue
                    for link in links if isinstance(links, list) else []:
                        if (
                            isinstance(link, list)
                            and len(link) >= 5
                            and link[0] == link_id
                        ):
                            src_text = node_text(nodes_by_id.get(link[1], {}))
                            if src_text:
                                prompts.append(src_text.strip())
            continue

        if node_type == "TextEncodeAceStepAudio1.5":
            text = node_text(node)
            if text:
                prompts.append(text.strip())
            continue

        proxy = node.get("properties", {}).get("proxyWidgets")
        if isinstance(proxy, list) and any(
            isinstance(p, list) and len(p) >= 2 and p[1] in ("prompt", "text", "value")
            for p in proxy
        ):
            text = node_text(node)
            if text:
                prompts.append(text.strip())

    return prompts


def _subgraph_lookup(doc: dict[str, Any], repo_root: Path) -> dict[str, dict[str, Any]]:
    embedded: dict[str, dict[str, Any]] = {}
    for subgraph in doc.get("definitions", {}).get("subgraphs", []):
        if isinstance(subgraph, dict) and isinstance(subgraph.get("id"), str):
            embedded[subgraph["id"]] = subgraph
    embed = _load_embed_module()
    donors = embed.build_donor_index(repo_root / "workflows")
    templates = embed.load_templates()
    for node in doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = node.get("type", "")
        if not isinstance(node_type, str) or not UUID_TYPE_RE.match(node_type):
            continue
        if node_type in embedded:
            continue
        body = embed.subgraph_for_id(node_type, templates, donors)
        if body is not None:
            embedded[node_type] = body
    return embedded


def iter_graphs(doc: dict[str, Any], repo_root: Path | None = None) -> Iterator[dict[str, Any]]:
    """Root graph, embedded subgraphs, and resolved UUID subgraph bodies."""
    yield {"nodes": doc.get("nodes", []), "links": doc.get("links", [])}
    root = repo_root or REPO_ROOT
    resolved = _subgraph_lookup(doc, root)
    seen: set[str] = set()
    for subgraph in doc.get("definitions", {}).get("subgraphs", []):
        if isinstance(subgraph, dict):
            sg_id = subgraph.get("id")
            if isinstance(sg_id, str):
                seen.add(sg_id)
            yield {"nodes": subgraph.get("nodes", []), "links": subgraph.get("links", [])}
    for sg_id, body in resolved.items():
        if sg_id in seen:
            continue
        yield {"nodes": body.get("nodes", []), "links": body.get("links", [])}


def embed_resolved_subgraphs(doc: dict[str, Any], repo_root: Path | None = None) -> list[str]:
    """Persist donor-resolved UUID subgraphs into definitions.subgraphs."""
    root = repo_root or REPO_ROOT
    resolved = _subgraph_lookup(doc, root)
    definitions = doc.setdefault("definitions", {})
    subgraphs: list[dict[str, Any]] = definitions.setdefault("subgraphs", [])
    existing = {sg.get("id") for sg in subgraphs if isinstance(sg, dict)}
    added: list[str] = []
    for sg_id, body in resolved.items():
        if sg_id in existing:
            continue
        subgraphs.append(copy.deepcopy(body))
        added.append(sg_id)
    return added


def extract_prompts(doc: dict[str, Any], repo_root: Path | None = None) -> list[str]:
    prompts: list[str] = []
    for graph in iter_graphs(doc, repo_root):
        prompts.extend(_prompts_from_graph(graph))
    seen: set[str] = set()
    unique: list[str] = []
    for prompt in prompts:
        if prompt and prompt not in seen:
            seen.add(prompt)
            unique.append(prompt)
    return unique


def set_widget_text(node: dict[str, Any], text: str) -> bool:
    values = node.get("widgets_values")
    if isinstance(values, list) and values:
        values[0] = text
        return True
    return False


def apply_prompts(
    doc: dict[str, Any],
    positive: str,
    negative: str,
    *,
    repo_root: Path | None = None,
    embed_subgraphs: bool = True,
) -> tuple[bool, int, int, int]:
    """Write positive/negative into all prompt-bearing nodes; optionally embed UUID subgraphs."""
    if embed_subgraphs:
        embed_resolved_subgraphs(doc, repo_root)

    changed = False
    pos_count = 0
    neg_count = 0
    fallback_count = 0
    root = repo_root or REPO_ROOT

    for graph in iter_graphs(doc, root):
        nodes = graph.get("nodes", [])
        links = graph.get("links", [])
        if not isinstance(nodes, list):
            continue
        nodes_by_id = {n.get("id"): n for n in nodes if isinstance(n, dict)}
        by_src = link_index(links if isinstance(links, list) else [])

        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = node.get("type", "")

            if node_type == "CLIPTextEncode":
                role = clip_encode_role(node, nodes_by_id, by_src)
                if role == "negative":
                    if negative and set_widget_text(node, negative):
                        changed = True
                        neg_count += 1
                else:
                    if set_widget_text(node, positive):
                        changed = True
                        pos_count += 1
                continue

            if node_type in ("PrimitiveStringMultiline", "Text Multiline"):
                title = str(node.get("title", "")).lower()
                if "neg" in title:
                    if negative and set_widget_text(node, negative):
                        changed = True
                        neg_count += 1
                    continue
                if set_widget_text(node, positive):
                    changed = True
                    pos_count += 1
                continue

            if node_type == "TextEncodeQwenImageEditPlus":
                title = str(node.get("title", "")).lower()
                if "neg" not in title and set_widget_text(node, positive):
                    changed = True
                    pos_count += 1
                continue

            if node_type == "TextEncodeAceStepAudio1.5":
                if set_widget_text(node, positive):
                    changed = True
                    pos_count += 1
                continue

            proxy = node.get("properties", {}).get("proxyWidgets")
            if isinstance(proxy, list) and any(
                isinstance(p, list) and len(p) >= 2 and p[1] in ("prompt", "text")
                for p in proxy
            ):
                values = node.get("widgets_values")
                if isinstance(values, list) and values and isinstance(values[0], str):
                    if set_widget_text(node, positive):
                        changed = True
                        pos_count += 1
                    continue

            if isinstance(node_type, str) and UUID_TYPE_RE.match(node_type):
                proxy = node.get("properties", {}).get("proxyWidgets")
                inputs = node.get("inputs", [])
                wv = list(node.get("widgets_values") or [])
                wrote = False
                if isinstance(proxy, list) and proxy:
                    if len(wv) < len(proxy):
                        wv.extend([""] * (len(proxy) - len(wv)))
                    for pi, entry in enumerate(proxy):
                        if not isinstance(entry, list) or len(entry) < 2:
                            continue
                        slot = entry[1]
                        if slot in ("text", "prompt"):
                            wv[pi] = positive
                            wrote = True
                            break
                for idx, inp in enumerate(inputs):
                    if not isinstance(inp, dict):
                        continue
                    label = str(inp.get("label", "")).lower()
                    inp_type = inp.get("type")
                    while len(wv) <= idx:
                        wv.append(False if inp_type == "BOOLEAN" else "")
                    if inp_type == "STRING" and "prompt" in label and "enhance" not in label:
                        wv[idx] = positive
                        wrote = True
                if wrote:
                    node["widgets_values"] = wv
                    changed = True
                    pos_count += 1

    return changed, pos_count, neg_count, fallback_count
