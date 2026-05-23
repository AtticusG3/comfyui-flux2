# Workflow semantics reference

Companion to structural validation. Ensures bundled pack workflows ship with **sensible defaults** for the model family and an **example prompt** that demonstrates what the pack can do.

Implementation: `scripts/validate_workflow_semantics.py` (invoked via `validate_workflow_json.py --semantics`).

Prompt extraction and apply logic is shared with `scripts/lib/workflow_prompts.py` (used by `scripts/update_workflow_prompts.py`). It walks:

- Root graph nodes
- `definitions.subgraphs` bodies
- **UUID subgraph instances** resolved from donors under `workflows/` and `workflows/_templates/`
- `TextEncodeQwenImageEditPlus`, `TextEncodeAceStepAudio1.5`, proxy `text`/`prompt` widgets on subgraph nodes

## Example prompt rubric

### Preferred T2I / photoreal pattern

Favour a **portrait of people with a car in a scenic location**:

| Anchor | Examples |
| ------ | -------- |
| People | portrait, driver, pilot, attendant, figures, crowd |
| Vehicle | car, Supra, Skyline, AE86, NSX, motorcycle, shinkansen |
| Scenic | mountain road, coast, sunset, hairpin, circuit, rain, city night |

Score 2 of 3 anchors = good. Missing anchors emit `semantics-warn` (not a hard fail).

### Pack-specific modes

| `prompt_mode` | Packs | Expectation |
| ------------- | ----- | ----------- |
| `portrait_car_scenic` | flux2, klein, realvisxl, z-image-turbo, flux1-krea, hidream-o1 | Photoreal scene; portrait + car + scenic preferred |
| `edit_instruction` | qwen-image-edit-2511, firered, sdxl-editing | Imperative edit ("Change X, keep Y") |
| `anime_portrait` | z-image-anime | Anime / illustration wording |
| `anime_scene` | newbie-image | Tagged or anime scene description |
| `video_motion` | wan-2-2 | Motion, camera, or animate language |
| `audio` | ace-step | BPM, key, instruments, style |
| `poster_or_graphic` | ovis-image | Poster / graphic design |
| `stylized` | ernie-image | Watercolor, vector, etc. |
| `product_or_studio` | z-image-base | Product / studio shot |
| `object` | hunyuan-3d | 3D object description |
| `skip` | hunyuan-video guide | No prompt gate |

Hard **prompt-quality** failures: empty prompt, placeholder text (`text`, `prompt`, `example`), or under 24 characters.

## Sampler / model defaults

Checked per pack via `PACK_PROFILES` in `validate_workflow_semantics.py`.

| Pack | Defaults checked |
| ---- | ---------------- |
| `qwen-image-edit-2511` | Lightning LoRA present; turbo toggle default **on**; step primitives **4** and **40**; CFG ~4 for lightning path |
| `firered-image-edit` | Lightning LoRA substring; step options |
| `sdxl-lightning` | 4- or 8-step primitives; CFG in lightning range |

General rules:

- Lightning packs must expose a **fast** step count (4 for Qwen/SDXL, 8 for FireRed) and a **full** option.
- LoRA filename must match pack download (`Lightning-4steps`, etc.) when `expect_lora_substr` is set.
- Distilled T2I packs should not default to 40+ steps on the primary path.

## Prompt registry

When a workflow path exists in `scripts/update_workflow_prompts.py` `SCENES`, the positive prompt embedded in the JSON should match that registry entry. Mismatch emits `prompt-registry` warning (drift between maintainer script and bundled JSON).

To refresh prompts across all workflows:

```bash
python scripts/update_workflow_prompts.py
```

## Fixing failures

| Gate | Fix |
| ---- | --- |
| `semantics` FAIL (defaults) | Adjust `PrimitiveInt`/`PrimitiveFloat`, LoRA widget, or turbo boolean in ComfyUI; re-export JSON |
| `semantics-warn` (prompt) | Rewrite example prompt; prefer portrait + car + scenic for photoreal T2I |
| `prompt-registry` | Run `update_workflow_prompts.py` or update `SCENES` and re-apply |

Do **not** satisfy structural gates by hand-editing `widgets_values` order. Re-export from ComfyUI when widget layout is unknown.

## Authoring new pack workflows

1. Add a `SCENES` entry in `update_workflow_prompts.py` before running the bulk updater.
2. Add or extend `PACK_PROFILES` in `validate_workflow_semantics.py` for the pack folder name.
3. Run full validation:

```bash
python scripts/validate_workflow_json.py --semantics --pack-audit workflows/<pack>/
```
