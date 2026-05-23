---
name: validate-comfyui-workflow
description: Validates ComfyUI workflow JSON against official ComfyWorkflow schemas (0.4 and 1.0), dangling links, and optional pack asset coverage. Use when validating, linting, or debugging workflows under workflows/, or when ComfyUI refuses to load a graph.
disable-model-invocation: true
---

# validate-comfyui-workflow

## When to use

- After editing any file under `workflows/**/*.json`.
- Before a PR that touches bundled pack workflows or workflow lists.
- When investigating "ComfyUI won't load this workflow" reports.

## Prerequisites

Python **3.10+** (schema validation uses `jsonschema` 4.x):

```bash
pip install jsonschema==4.26.0
```

On Windows, if default `python` is 3.9, use `py -3.12` instead.

## Format dispatch (by file content)

| Shape | Format | Schema |
| ----- | ------ | ------ |
| `version: 0.4`, `last_node_id`, tuple `links[]` | **ComfyWorkflow 0.4** | `schemas/comfy/workflow-definition-v0.4.json` |
| `version: 1`, `state.*`, object `links[]` | **ComfyWorkflow 1.0** | `schemas/comfy/workflow-definition-v1.0.json` |
| Top-level map of `class_type` + `inputs` | **API / prompt** | Not validated here; use comfy-router |

Pack workflows in this repo are almost always **0.4** (ComfyUI litegraph export). Do not require v1.0 `state` on them.

Official specs: [workflow_json (1.0)](https://docs.comfy.org/specs/workflow_json), [workflow_json_0.4](https://docs.comfy.org/specs/workflow_json_0.4). See [reference.md](reference.md).

## Gates

| Gate | Tool | Failure means |
| ---- | ---- | ------------- |
| JSON parse | `scripts/validate_workflow_json.py` | Malformed JSON |
| Format | same | Cannot tell 0.4 vs 1.0 vs API |
| Schema | same (`jsonschema`) | Missing required fields vs official schema |
| Links | same | Dangling node id in `links[]` |
| Pack audit (optional) | `--pack-audit` -> `audit_workflow_assets.py` | Model/node not in pack catalogs |

## Procedure

1. List target paths (files or directories; default `workflows/`).
2. Run:

```bash
python scripts/validate_workflow_json.py <path> [<path> ...]
```

Optional pack model/node coverage:

```bash
python scripts/validate_workflow_json.py --pack-audit workflows/
```

3. Aggregate output. Exit code `0` only if every gate passes for every file (and pack-audit if requested).

## Output format

ASCII-only. One line per result:

```text
<path>  <gate>  PASS|FAIL  [<message>]
```

Schema passes are tagged `schema-ComfyWorkflow0_4` or `schema-ComfyWorkflow1_0`.

## Reject conditions

- Do **not** auto-fix failures from this skill. Report and stop.
- Do **not** edit vendored schemas under `schemas/comfy/` to make a workflow pass.
- Do **not** hand-edit `widgets_values`, node ids, or `state` / `last_node_id` counters to satisfy the validator.
- Do **not** pretty-print or round-trip workflow JSON through a formatter (widget order is fragile).

## comfy-router (kernel workflows)

For the sibling **comfy-router** repo (`workflows/subgraphs/`, `workflows/exports/*_UI.json`, `*_API.json`):

- Use `.cursor/skills/validate_workflow.md` and `python .cursor/hooks/post-edit.py <path>` for contract enums, node-ref, and prompt-format draft schema.
- F-004 litegraph relaxation applies only to immutable `workflows/exports/*_UI.json` in comfy-router, not to pack JSON here.

## Additional resources

- [reference.md](reference.md) -- 0.4 vs 1.0 field reference and gate mapping
- [schemas/comfy/.provenance.md](../../../schemas/comfy/.provenance.md) -- vendored schema sources
