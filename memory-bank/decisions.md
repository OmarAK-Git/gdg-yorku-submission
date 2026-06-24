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
- **Decision**: Account for contested findings by placing them in the dedicated `contested` ledger bucket (4-bucket design).
- **Rationale**: Keeps the conservation equation clean (`included U merged_inputs U omitted U contested == total_inputs`) and prevents active contested findings from appearing in the main report findings list. The validator explicitly handles contested findings separately.
- **Decision**: `status` is a merge isolation boundary alongside `perspective` and `source_agent`; a contested finding can never be merged into an active finding.
- **Rationale**: The coordinator is LLM-driven and was non-deterministically merging contested security findings into a single active finding (status precedence `active > contested` silently promoted the result), erasing them from the contested set while conservation accounting still passed (they hid under "Merged"). Enforced in both the compiler (skips the merge + feedback retry) and the validator (invariant violation). Preserves the human-in-the-loop contested workflow.

## Generative Debate Grounding (Recall vs. Hallucination)
- **Decision**: Ground generative debate findings by *truth*, not by citation *format*. `resolve_generative_citation` accepts a free-text citation (path may be embedded in prose; line ref may be `#14-37`, `lines 14-37`, `line 23`, or absent → whole-file span) and grounds it iff the path matches a real corpus file and the lines are in-bounds. A citation to a non-existent file or out-of-bounds lines is still dropped.
- **Rationale**: The earlier strict parser required an exact `path#start-end` anchor and silently dropped substantively valid findings whose citation merely had trailing prose ("#14-37 (entire function)") or a prose line ref ("at line 23"). That cost real recall for zero safety gain — the anti-hallucination guarantee comes entirely from the corpus-path + in-bounds checks, not from citation syntax. This reverses the Task-24 close-out decision to keep the parser strict; the hallucination guard (cited location must actually exist) is fully preserved. The schema field description now requests the clean `path#start-end` anchor so the model still aims for it.
