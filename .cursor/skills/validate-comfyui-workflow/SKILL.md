---
name: validate-comfyui-workflow
description: Validates ComfyUI workflow JSON (ComfyWorkflow 0.4/1.0 schemas, links, pack assets) and semantic checks for model-appropriate sampler defaults and example prompts. Use when validating, linting, or debugging workflows under workflows/, or when ComfyUI refuses to load a graph.
disable-model-invocation: true
---

# validate-comfyui-workflow

## When to use

- After editing any file under `workflows/**/*.json`.
- Before a PR that touches bundled pack workflows or workflow lists.
- When investigating "ComfyUI won't load this workflow" reports.
- When reviewing whether the **default prompt** and **sampler defaults** match the pack (Lightning steps, LoRA toggle, edit instructions).

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
| Topology | `--topology` -> `validate_workflow_topology.py --check-wrapper` | Root/subgraph link drift or wrapper/subgraph interface mismatch |
| Semantics | `--semantics` -> `validate_workflow_semantics.py` | Wrong Lightning steps/LoRA defaults; empty or placeholder prompt |
| Semantics warn | same (`semantics-warn` lines) | Prompt missing portrait/car/scenic anchors or registry drift |
| Pack audit (optional) | `--pack-audit` -> `audit_workflow_assets.py` | Model/node not in pack catalogs |

## Procedure

1. List target paths (files or directories; default `workflows/`).
2. Run structural validation:

```bash
python scripts/validate_workflow_json.py <path> [<path> ...]
```

3. Add semantic checks (defaults + example prompts):

```bash
python scripts/validate_workflow_json.py --semantics <path> [<path> ...]
```

Include topology parity when workflows have embedded UUID subgraphs:

```bash
python scripts/validate_workflow_json.py --semantics --topology <path> [<path> ...]
```

Full maintainer pass before a pack workflow PR:

```bash
python scripts/validate_workflow_json.py --semantics --pack-audit workflows/<pack>/
```

Optional: semantics only on one file:

```bash
python scripts/validate_workflow_semantics.py workflows/qwen-image-edit-2511/qwen-edit-2511.json
```

4. Aggregate output. Exit code `0` only if every gate passes for every file (and optional flags requested).

## Semantics (defaults + prompts)

See [semantics-reference.md](semantics-reference.md) for the full rubric.

**Example prompts** -- favour a **portrait of people with a car in a scenic location** for photoreal T2I packs (flux, SDXL, RealVisXL, Z-Image turbo, etc.). Missing anchors are warnings, not hard fails.

**Edit packs** (Qwen Image Edit 2511, FireRed, SDXL editing) -- use a clear edit instruction ("Change X, keep pose and background").

**Lightning packs** -- verify:

- `LoraLoaderModelOnly` references the pack Lightning file
- Fast path uses the expected step count (4 for Qwen/SDXL Lightning)
- Turbo / "Enable 4steps LoRA" defaults **on** when the pack ships Lightning-first (Qwen 2511)

**Registry** -- bundled JSON should match `SCENES` in `scripts/update_workflow_prompts.py`. Refresh with:

```bash
python scripts/update_workflow_prompts.py
```

## Output format

ASCII-only. One line per result:

```text
<path>  <gate>  PASS|FAIL  [<message>]
```

Schema passes are tagged `schema-ComfyWorkflow0_4` or `schema-ComfyWorkflow1_0`.

Semantic warnings use gate `semantics-warn` and do not fail the run unless paired with a `semantics` FAIL.

## Reject conditions

- Do **not** auto-fix failures from this skill. Report and stop.
- Do **not** edit vendored schemas under `schemas/comfy/` to make a workflow pass.
- Do **not** hand-edit `widgets_values`, node ids, or `state` / `last_node_id` counters to satisfy the validator.
- Do **not** pretty-print or round-trip workflow JSON through a formatter (widget order is fragile).
- Do **not** weaken `PACK_PROFILES` or prompt rubrics to silence warnings without user intent.

## comfy-router (kernel workflows)

For the sibling **comfy-router** repo (`workflows/subgraphs/`, `workflows/exports/*_UI.json`, `*_API.json`):

- Use `.cursor/skills/validate_workflow.md` and `python .cursor/hooks/post-edit.py <path>` for contract enums, node-ref, and prompt-format draft schema.
- F-004 litegraph relaxation applies only to immutable `workflows/exports/*_UI.json` in comfy-router, not to pack JSON here.

## Additional resources

- [reference.md](reference.md) -- 0.4 vs 1.0 field reference and gate mapping
- [semantics-reference.md](semantics-reference.md) -- prompt rubric and per-pack default expectations
- [schemas/comfy/.provenance.md](../../../schemas/comfy/.provenance.md) -- vendored schema sources
