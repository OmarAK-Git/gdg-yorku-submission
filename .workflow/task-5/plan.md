# Task 5: Hardened Zip Extraction Plan

## Scope
Implement zip extraction safety checks (size caps, count caps, directory traversal blocks, entry skipping).

## Components to modify/create

1. `src/gdg_yorku_submission/ingestion.py` [NEW]
   - Create `ZipIngestor` class.
   - Constants for caps: 50MB compressed, 500MB uncompressed, 10000 file count, 50MB per file.
   - Implement `extract_archive(content: bytes, workspace_dir: str) -> IngestionManifest`
   - Implement checks for directory traversal (`os.path.abspath(os.path.join(...)).startswith(workspace)`)
   - Implement skipping logic for inner archives, absolute paths, symlinks, and system excludes (`.venv`, `*.db`, etc.).
   - Return a manifest containing `extracted_files` and `skipped_files` (with `skipped_reason`).

2. `src/gdg_yorku_submission/schemas.py` [MODIFY]
   - Ensure `CorpusSummary` exists or add `IngestionManifest` to represent the extraction results and pass to the Orchestrator.

3. `src/gdg_yorku_submission/app.py` [MODIFY]
   - Call `ZipIngestor.extract_archive` in the `/review` endpoint.
   - Update the `corpus_summary` from the hardcoded stub to the real summary based on the manifest.

4. `tests/test_ingestion.py` [NEW]
   - Test that uncompressed size bombs abort the extraction.
   - Test that file count bombs abort the extraction.
   - Test that traversal attempts are skipped.
   - Test that nested archives are skipped.

## Constraints
- Do not modify `docs/`.
- Do not exceed the scope of Task 5.
