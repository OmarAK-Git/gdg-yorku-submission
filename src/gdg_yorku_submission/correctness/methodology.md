# Correctness Review Rubric and Methodology

This document outlines the standard evaluation criteria and structured methodology for the correctness review perspective.

## Core Mandate
Verify and analyze the implementation code against the discovered Source of Truth (SoT) specification and design documents. The goal is to detect code-specification divergence, assess logic-vs-spec consistency, check intent matching, and enforce traceability.

## Evaluation Categories

### 1. Intent Extraction & Verification
Verify that the implemented logic matches the explicit requirements and core intent defined in the SoT.
- Verify function signatures, class interfaces, and control flow alignment with specification descriptions.
- Ensure behavior matches documented business rules and domain logic.

### 2. Spec-Code Divergence
Divergences between the Source of Truth and the implementation code must be documented neutrally.
- Tone must be direction-neutral: do not assume either the spec or the code is wrong.
- Emitted prose must state facts without bias, e.g., "The code at `path/to/file.py#L10-L15` implements X, whereas SPEC.md at `line 20` specifies Y."

### 3. Traceability
Every divergence or conformance finding must cite exact locations in both the implementation files and the SoT evidence.
- Both finding `location` and `evidence_ref` must use the original file coordinates system: `file:path#line_start-line_end`.

### 4. Logic-vs-Spec Consistency
Verify that the code's internal logic is consistent with the specified design invariants and interface assumptions.

## Severity Constraints
Findings must map to the unified severity vocabulary: `critical`, `high`, `medium`, `low`, or `info`.

- **No-Spec Fallback Severity Cap**: If no specification is found (status `no_spec_found_conformance_skipped`), any logic-consistency finding must be based strictly on internal code consistency (docstring vs signature, obvious self-contradictions) and is strictly capped at a maximum severity of `medium`. It must cite concrete, existing in-code evidence.

## Finding Schema Requirements
All correctness findings must match the unified finding schema.

Required to emit:
- `id`
- `source_agent`
- `perspective`
- `severity`
- `location`
- `claim`
- `evidence_ref`

Present in schema (defaulted if omitted):
- `status`
- `metadata`
