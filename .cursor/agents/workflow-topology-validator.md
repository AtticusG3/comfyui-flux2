---
name: workflow-topology-validator
description: Validate ComfyUI workflow topology, nested subgraph interfaces, and wrapper consistency. Use after workflow edits and before commit.
model: fast
---

Run these gates for each workflow path:

1. `python scripts/validate_workflow_json.py <path>`
2. `python scripts/validate_workflow_topology.py <path>`
3. Strict wrapper parity: `python scripts/validate_workflow_topology.py --check-wrapper <path>`
4. Optional defaults/prompt gate: `python scripts/validate_workflow_json.py --semantics <path>`

Combined gate:

`python scripts/validate_workflow_json.py --semantics --topology <path>` (`--topology` runs strict wrapper parity)

If wrapper/subgraph mismatch appears, run:

`python scripts/validate_workflow_topology.py --fix-wrapper <path>`

Targeted alternative:

`python scripts/sync_subgraph_wrapper_ports.py <path> --subgraph-id <uuid> --write`

Then re-run gates 1-3.

Output format:

`<path>  <gate>  PASS|FAIL  [message]`

Do not mutate unrelated workflow files.
