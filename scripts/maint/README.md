# Maintainer one-off scripts

Historical migration and pack-repair utilities. Not used at container startup.

| Script | Purpose |
| --- | --- |
| `rename_workflows_short.py` | One-time rename to short kebab-case workflow filenames and manifest sync (completed in v1.7.0). |
| `replace_saveimageplus.py` | Replace `LayerUtility: SaveImagePlus` with core `SaveImage` across `workflows/` (completed in v1.7.0). |
| `fix_qwen_edit_workflow.py` | Normalize `qwen-edit-2511.json` model references after pack catalog changes. |

Re-run only when intentionally replaying a migration. Prefer the operational scripts in `scripts/README.md` for day-to-day maintainer work.
