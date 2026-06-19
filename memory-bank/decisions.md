# Decisions

This file records major architectural and design decisions, their contexts, and rationales.

## Ingestion & Exposure Model
- **Decision**: Ingest `.zip` files only; folders are deferred to V1.1.
- **Rationale**: Keeps backend input sanitization scope manageable.
- **Decision**: Skip nested archives, symlinks, absolute paths, and path-traversal entries with `skipped_reason` instead of aborting. Abort only when aggregate caps (sizes/counts) are exceeded.
- **Rationale**: Prevents zip bombs from crashing the system while allowing valid components of complex archives (e.g. wheels, jars) to be reviewed.
- **Decision**: Decouple secret-scan scope (full extracted corpus) from LLM prompt scope (`prompt_exposed` files).
- **Rationale**: Secrets often hide in gitignored files like `.env`, which must be scanned. However, gitignored files should not be sent to LLM prompt context to prevent unnecessary token usage and potential leak vectors.

## Security & Reliability Architecture
- **Decision**: Build the deterministic AST-based security pass *before* the debate as an always-on baseline.
- **Rationale**: Guarantees a valid security review perspective even if the debate loop is cut, fails, or runs out of budget.
- **Decision**: Coordinate through an Orchestrator abstraction seam.
- **Rationale**: Insulates the core logic from Google ADK implementation risks, ensuring an easy swap to a simple Python fallback.
- **Decision**: Bounded coordinator regeneration and deterministic terminal report fallback.
- **Rationale**: If the coordinator fails, exceeds retries, or runs out of budget, a schema-valid, fully-accounted terminal report is generated with zero LLM tokens. This guarantees reliability.

## Prompt & Data Safety
- **Decision**: Delimiter nonces for evidence plane.
- **Rationale**: Nonced random delimiters prevent prompt-injection attacks from untrusted repository content (like SPEC.md or code comments).
- **Decision**: Strict system-wide secret redaction invariant.
- **Rationale**: Raw secrets are never propagated to LLM prompts, logs, traces, validator errors, or frontend JSON. Spans are replaced with placeholders, and fingerprints are generated using a salted hash (per-run salt) to prevent last-4 leakage of short secrets.

## Finding Traceability
- **Decision**: Orchestrator-owned ID-finalization stage.
- **Rationale**: Freeze IDs using deterministic anchors before running the coordinator. Group and assign occurrence ordinals to distinct findings at the same file/line to prevent hidden omissions.
- **Decision**: Severity enum mapping (Blocker → `critical`, Security-Blocker → `high`, Major → `medium`, Minor → `low`, Observational → `info`).
- **Rationale**: Standardizes diverse client terminology with a reporting floor of `high`.
- **Decision**: Syntactic coordinate validation.
- **Rationale**: The validator verifies that all finding coordinates (`evidence_ref`) point to lines within the actual corpus/SoT bounds to prevent hallucinated citations.
- **Decision**: Account for contested findings by placing them in the `omitted` ledger bucket with the reason prefix `"Contested:"`.
- **Rationale**: Keeps the conservation equation clean (`included U merged_inputs U omitted == total_inputs`) and prevents active contested findings from appearing in the main report findings list. The Task 14 validator must explicitly exempt contested findings (present in `contested_items`) from the "reject any report that omits a high/critical finding" rule.
