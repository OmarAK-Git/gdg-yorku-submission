# Active Context

## Current State
- Core Pydantic V2 schemas, legacy-to-standard severity mapping, collision-safe ID finalization, and FastAPI walking skeleton / Orchestrator abstraction seam are completed and verified.
- Hardened Zip Extraction (Task 5) is completed and verified.
- Exposure-Model Prompt Corpus (Task 6) is implemented and verified.
- Secret Scanner + Redaction Invariant (Task 7) is completed, porting the secret gate detection, redaction invariant, and salted hash fingerprints.
- Evidence-Plane Prompt Builder (Task 8) is completed, building a nonced, sanitized, and redacted prompt representation of the prompt-exposed corpus.
- Full pytest suite (120 tests) passes with no warnings or errors.

## Active Focus
- Address Sprint 2 Gate Review findings:
  1. Thread a per-run `RedactionContext` in `start_run()` rather than using the process-global context, and disable the global context.
  2. Persist the redacted, exposure-classified `CorpusFile` dict in the Orchestrator shared state.
  3. Formally descope system-excludes and binaries from the secret scanner scan scope (due to performance and footprint boundaries) and update documents/tests.
  4. Enforce the `redaction_applied` precondition in the evidence plane builder and add an integration test.
  5. Add an HTTP E2E review upload test with synthetic secrets.
  6. Match `env` system exclude directories precisely (via virtualenv structure check) rather than skipping all directories named `env`.

## Next Steps
1. Refactor `RedactionContext` instantiation, disable global context, and update `Orchestrator` / `run_secret_scan` signatures.
2. Update Orchestrator state schema and conformance tests to store/retrieve the corpus.
3. Update `docs/spec.md`, `docs/plan.md`, and ingestion tests to explicitly state and verify the system-exclude scan descope.
4. Add `redaction_applied` to `CorpusFile` model and enforce it in the evidence plane builder; implement the integration test.
5. Add the HTTP E2E secret scan API test.
6. Implement precise virtualenv directory detection in `ingestion.py`.
