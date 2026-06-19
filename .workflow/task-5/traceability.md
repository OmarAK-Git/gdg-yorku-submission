# Traceability for Task 5

## Requirements
- **Zip Extraction**: Extract ZIP file safely (R1).
- **Caps**: Aggregate size caps (uncompressed bytes, file count, per-file bytes).
- **Skips**: Per-entry skips (symlinks, traversals, inner archives) without aborting.

## Code Map
- `src/gdg_yorku_submission/ingestion.py`: Implements zip extraction caps and skip logic.
- `src/gdg_yorku_submission/app.py`: Integrates extraction into upload endpoint.
- `tests/test_ingestion.py`: Verifies safety limits and skips.
