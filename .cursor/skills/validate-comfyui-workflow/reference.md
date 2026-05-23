# ComfyUI workflow JSON reference

Distilled from official Comfy specs and comfy-router validation patterns.
Full machine-readable schemas live in `schemas/comfy/`.

## Official sources

| Document | URL |
| -------- | --- |
| Workflow JSON 1.0 (`ComfyWorkflow1_0`) | https://docs.comfy.org/specs/workflow_json |
| Workflow JSON 0.4 (`ComfyWorkflow0_4`) | https://docs.comfy.org/specs/workflow_json_0.4 |
| Workflow concepts | https://docs.comfy.org/development/core-concepts/workflow |
| Node definition 1.0 | https://docs.comfy.org/specs/nodedef_json_1_0 |
| Schema change process | https://github.com/comfy-org/rfcs |
| Docs index (llms.txt) | https://docs.comfy.org/llms.txt |

## ComfyWorkflow 0.4 (this repo default)

**Required top-level keys:** `last_node_id`, `last_link_id`, `nodes`, `links`, `version` (typically `0.4`).

**Counters:** `last_node_id`, `last_link_id` at top level (not under `state`).

**Links:** array of 6-tuples:

```text
[link_id, origin_id, origin_slot, target_id, target_slot, type]
```

**Nodes:** each node requires `id`, `type`, `pos`, `size`, `flags`, `order`, `mode`, `properties`.
Optional: `inputs`, `outputs`, `widgets_values`, `title`, `color`, etc.

**Vendored schema:** `schemas/comfy/workflow-definition-v0.4.json`

## ComfyWorkflow 1.0

**Required top-level keys:** `version` (const `1`), `state`, `nodes`.

**Counters:** under `state`: `lastNodeId`, `lastLinkId`, `lastGroupid`, `lastRerouteId`.

**Links:** array of objects with `id`, `origin_id`, `origin_slot`, `target_id`, `target_slot`, `type`.

**Vendored schema:** `schemas/comfy/workflow-definition-v1.0.json`

## API / prompt format (not validated in comfyui-flux2)

Object keyed by node id string. Each value:

```json
{
  "class_type": "NodeType",
  "inputs": {
    "param": "value",
    "other": ["source_node_id", 0]
  }
}
```

Validate in **comfy-router** with `schemas/nodes/prompt-format-DRAFT.json` and `post-edit.py`.

## Gate mapping: flux2 vs comfy-router

| Concern | comfyui-flux2 (`validate_workflow_json.py`) | comfy-router |
| ------- | -------------------------------------------- | ------------ |
| JSON parse | yes | yes (`post-edit.py`) |
| UI schema 0.4 | yes | no (expects 1.0 or F-004 exports) |
| UI schema 1.0 | yes | yes |
| Dangling links (UI) | yes (tuple + object) | yes |
| Dangling links (API) | basic ref check only | yes |
| Contract enums (`family`, `mode`, `aspect`) | no | yes |
| Node-ref vs exports/schemas | no | yes |
| Pack models/nodes | `audit_workflow_assets.py` (`--pack-audit`) | N/A |
| Example prompts / sampler defaults | `validate_workflow_semantics.py` (`--semantics`) | N/A |

## Widget values warning

`widgets_values` order matches each node's `INPUT_TYPES` in the running ComfyUI build.
Reformatting JSON or reordering the array silently breaks inference. Prefer re-export from ComfyUI over hand edits.

## Failure modes (cross-repo)

- **F-004 (comfy-router only):** legacy exports with `last_node_id` / `last_link_id` and no `state` load in ComfyUI but fail strict 1.0 schema. Pack workflows here are legitimately **0.4**, not F-004.
- **Schema drift:** hand-authored graphs missing required fields; restore from ComfyUI export.
