# Active Context

## Current State
- Core Pydantic V2 schemas, legacy-to-standard severity mapping, collision-safe ID finalization, and FastAPI walking skeleton / Orchestrator abstraction seam are completed and verified.
- Hardened Zip Extraction (Task 5) is completed and verified.
- Exposure-Model Prompt Corpus (Task 6) is implemented and verified, including root gitignore wildmatch parsing using `pathspec`, exposure status classification, and original-coordinate `CorpusFile` mappings.
- Full pytest suite (94 tests) passes with no warnings or errors.

## Active Focus
- Preparing for Sprint 2 / **Task 7 — Secret Scanner + Redaction Invariant**:
  - Port Tumbler secret scan, redact secrets from prompts/logs, and implement salted hash fingerprints.

## Next Steps
1. Port Tumbler secret scanner detection rules.
2. Implement central `RedactionContext` to manage secret spans, placeholders, and salt-hashed fingerprints.
3. Integrate pre-flight secret gate scans into orchestrator/pipeline.
4. Write unit tests to verify secrets redaction and fingerprint hashing.
