# Tasks

This file tracks the status, dependencies, and references for all implementation tasks.

## Sprint 1: Walking Skeleton & Schema Configuration
- [x] **Task 1 — Fresh Repo Baseline + Provenance Guard**
  - **Description**: Establish git log commit window guard (`scripts/check_commit_window.py` for commits ≥ 2026-06-17) and create `NOTICE.md` provenance table.
  - **Dependencies**: None
  - **References**: [R10]
- [x] **Task 2 — Core Schemas + Severity Mapping**
  - **Description**: Define finding/report schemas, validate severities, map blocker/major/minor → critical/high/medium/low. Floor = `high`.
  - **Dependencies**: Task 1
- [x] **Task 3 — Collision-Safe Deterministic Finding IDs**
  - **Description**: Implement stable ID generation with occurrence ordinals for co-located findings.
  - **Dependencies**: Task 2
  - **References**: [R8]
- [x] **Task 4 — FastAPI Walking Skeleton + Orchestrator Seam**
  - **Description**: Implement upload API with stubs, Orchestrator seam interface, and plain-Python vs. ADK conformance test.
  - **Dependencies**: Tasks 1, 2, 3
  - **References**: [R8]

## Sprint 2: Deterministic Trust Boundary
- [x] **Task 5 — Hardened Zip Extraction**
  - **Description**: Implement zip extraction safety checks (size caps, count caps, directory traversal blocks, entry skipping).
  - **Dependencies**: Task 4
  - **References**: [R1]
- [x] **Task 6 — Exposure-Model Prompt Corpus**
  - **Description**: Wrap files as `CorpusFile` models, categorize by exposure status, and filter with root `.gitignore`.
  - **Dependencies**: Task 5
  - **References**: [R2], [R5]
- [x] **Task 7 — Secret Scanner + Redaction Invariant**
  - **Description**: Port Tumbler secret scan, redact secrets from prompt/logs, and implement salted hash fingerprints.
  - **Dependencies**: Tasks 5, 6
  - **References**: [R3]
- [x] **Task 8 — Evidence-Plane Prompt Builder (Nonced)**
  - **Description**: Delimit untrusted content using per-run random nonced separators.
  - **Dependencies**: Tasks 6, 7

## Sprint 2 Gate Review Fixes
- [x] **Gate Fix 1 — Threaded Per-Run RedactionContext**
- [x] **Gate Fix 2 — Redacted Corpus in Orchestrator Shared State**
- [x] **Gate Fix 3 — Descope System Excludes from Scan (Explicit & Documented)**
- [x] **Gate Fix 4 — Evidence Plane Seam & Precondition Verification**
- [x] **Gate Fix 5 — HTTP E2E Secret Scan Review Test**
- [x] **Gate Fix 6 — Precise Virtualenv Directory Excludes**

## Sprint 3: Correctness Agent & Baseline Security
- [ ] **Task 9 — Source-of-Truth Discovery**
  - **Description**: Discover spec files (SPEC.md, DESIGN.md, allowed README headers) and define no-spec fallback.
  - **Dependencies**: Task 8
  - **References**: [R2]
- [ ] **Task 10 — Rewrite Correctness Rubric/Methodology**
  - **Description**: Author correctness-only review criteria, capping no-spec findings at `medium`.
  - **Dependencies**: Task 9
- [ ] **Task 11 — Deterministic Security Baseline Pass (Python AST)**
  - **Description**: Implement deterministic Python AST checkers (SQLi, shell=True, unsafe deserialize, missing auth, path traversal, verify=False).
  - **Dependencies**: Tasks 5, 6, 7, 8
  - **References**: [R6]
- [ ] **Task 12 — Correctness Agent Adapter**
  - **Description**: Adapter for Vertex AI Gemini correctly grounded via evidence-refs and budget-aware.
  - **Dependencies**: Tasks 8, 9, 10
  - **References**: [R5], [R7]

## Sprint 4: Coordination & Validation
- [ ] **Task 13 — Coordinator Compiler**
  - **Description**: Implement coordinator agent to group/merge findings within same perspective/source and output a consolidated report.
  - **Dependencies**: Tasks 2, 4, 11, 12
  - **References**: [R4], [R8]
- [ ] **Task 14 — Conservation Validator**
  - **Description**: Validate reports deterministic invariants (no high omission, correct merge severity, coordinate existence).
  - **Dependencies**: Task 13
  - **References**: [R4], [R5]
- [ ] **Task 15 — Bounded Regeneration + Deterministic Terminal Report**
  - **Description**: Bounded retry loop for validator failures falling back to zero-LLM terminal report.
  - **Dependencies**: Task 14
  - **References**: [R7]
- [ ] **Task 16 — Pinned Demo Sample**
  - **Description**: Build and verify demo repo `samples/driftstore` to trigger required review findings.
  - **Dependencies**: Tasks 5, 6, 7, 8, 9, 11
- [ ] **Task 17 — Frontend Report Viewer**
  - **Description**: Renders HTML/JS view for review findings, statuses, ledger, and secret summary.
  - **Dependencies**: Tasks 4, 14
  - **References**: [R4]
- [ ] **Task 18 — Out-of-Band Validator-Rejection Demo Hook**
  - **Description**: CLI demo script showing validation failure on manually corrupted report, isolated from HTTP path.
  - **Dependencies**: Task 14
  - **References**: [R9]

## Upgrades (Strictly Optional)
- [ ] **Task 19 — Debate Data Model**
  - **Description**: Schemas for debate rounds: candidates, survived, defeated, contested.
  - **Dependencies**: Task 2
  - **References**: [R4]
- [ ] **Task 20 — Port Crucible Debate Loop**
  - **Description**: Tuned stop conditions (stability and token limits), scoring metrics.
  - **Dependencies**: Task 19
- [ ] **Task 21 — Security Debate Adapter**
  - **Description**: Integrate debate loop with Claude/Gemini, with baseline fallback on failure.
  - **Dependencies**: Tasks 7, 8, 20
  - **References**: [R7]
- [ ] **Task 22 — Optional Orbit Blast-Radius**
  - **Description**: Impact analysis via GitLab Knowledge Graph; fails safe if unconfigured.
  - **Dependencies**: Task 2

## Close-Out
- [ ] **Task 23 — End-to-End Tests**
  - **Description**: Integration test verifying complete run, secret redactions, fallback.
  - **Dependencies**: Tasks 15, 16, 17
  - **References**: [R3]
- [ ] **Task 24 — Real-LLM Smoke Script**
  - **Description**: Live run wrapper script for dry run or actual integration tests.
  - **Dependencies**: Tasks 12, 15, 16
  - **References**: [R10]
- [ ] **Task 25 — README + Writeup + Provenance**
  - **Description**: Documentation: setup, architecture, provenance table, user instructions.
  - **Dependencies**: Stable core
  - **References**: [R10]
- [ ] **Task 26 — Evidence + Recording Prep**
  - **Description**: Run demo scripts, gather logs, screenshots, and record demo video.
  - **Dependencies**: Tasks 17-25
