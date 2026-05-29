---
name: workflow-subgraph-engineering
description: Deterministic workflow and embedded-subgraph editing for ComfyUI JSON in this repo. Use when changing UUID subgraph wrappers, repairing links, adding EmptyFlux2LatentImage paths, or validating root/subgraph topology without guessing.
disable-model-invocation: true
---

# workflow-subgraph-engineering

## When to use

- After editing `workflows/**/*.json` with embedded UUID subgraphs.
- When wrapper ports and subgraph interfaces drift.
- When ComfyUI throws link/slot/load errors and manual edits are risky.

## Procedure

1. Run structural validation first:

```bash
python scripts/validate_workflow_json.py <path>
```

2. Run deterministic topology checks:

```bash
python scripts/validate_workflow_topology.py <path>

# strict wrapper/subgraph interface parity
python scripts/validate_workflow_topology.py --check-wrapper <path>
```

3. If wrapper ports drift from embedded subgraph inputs/outputs, sync from source-of-truth subgraph interface:

```bash
# auto-fix all wrapper drift in file, then strict-validate wrappers
python scripts/validate_workflow_topology.py --fix-wrapper <path>
```

Targeted sync (single subgraph) is also available:

```bash
python scripts/sync_subgraph_wrapper_ports.py <path> --subgraph-id <uuid> --write
python scripts/sync_subgraph_wrapper_ports.py <path> --subgraph-name "Generate Image" --write
```

4. Re-run full checks:

```bash
python scripts/validate_workflow_json.py --semantics --topology <path>  # includes strict wrapper parity
```

## Deterministic rules

- Embedded subgraph `definitions.subgraphs[*]` is source of truth for wrapper port shape.
- Wrapper sync/parity logic lives in `scripts/lib/workflow_subgraph_ports.py`; keep wrappers and topology CLIs in lockstep with that library.
- Do not invent node types, slot indices, or link ids.
- Keep ASCII-only script output (`PASS`/`FAIL`, `[OK]`, `[WARN]`, `[ERROR]`).
- Do not touch unrelated subgraphs in the same file unless asked.

## Additional reference

See [reference.md](reference.md).
