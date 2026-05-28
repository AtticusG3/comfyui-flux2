# workflow-subgraph-engineering reference

## Commands

- Structural + schema:

```bash
python scripts/validate_workflow_json.py <path>
```

- Topology consistency (root + subgraphs + wrappers):

```bash
python scripts/validate_workflow_topology.py <path>

# strict wrapper interface parity
python scripts/validate_workflow_topology.py --check-wrapper <path>
```

- Wrapper auto-fix and strict validation in one command:

```bash
python scripts/validate_workflow_topology.py --fix-wrapper <path>
```

- Targeted wrapper port sync from embedded subgraph interface:

```bash
python scripts/sync_subgraph_wrapper_ports.py <path> --subgraph-id <uuid> --write
```

## Topology checks covered

- Dangling source/target nodes in root links and subgraph links.
- Missing per-node `inputs[].link` references.
- Missing per-node `outputs[].links` references.
- Wrapper UUID node input/output count and type mismatch against embedded subgraph interface.

## Typical repair loop

1. `validate_workflow_topology.py` -> read first failing wrapper/subgraph message.
2. `sync_subgraph_wrapper_ports.py --write` for the target UUID subgraph.
3. Rewire any intentional behavior changes in the subgraph body.
4. Re-run `validate_workflow_json.py --semantics --topology`.
