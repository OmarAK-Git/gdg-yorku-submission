# Document 2 — Implementation Plan (Critic-Finalized)

> **Headline:** the deterministic security pass is built **before** the debate and is the always-on baseline, so an end-to-end *valid* path (skeleton → secret gate → correctness → deterministic security → coordinator+validator → terminal-report safety net) exists by Day 5. Debate and Orbit are strict upgrades, cut without breaking the core. Severity-enum reconciliation, ID-collision/finalization, archive-bomb defenses, delimiter nonce, original-coordinate evidence, shared budget, and universally-reachable terminal report are explicit tasks. Repair-brief fixes R1–R10 are tagged on the tasks they touch.

## Sprint Groupings
- **Sprint 1 (Day 1):** Walking skeleton + schemas + severity mapping + collision-safe IDs.
- **Sprint 2 (Days 2–3):** Deterministic trust boundary — hardened zip extraction, exposure-model corpus, full-corpus secret scan, redaction invariant, nonced evidence plane.
- **Sprint 3 (Days 3–5):** Correctness agent + always-on deterministic security baseline + (upgrade) debate.
- **Sprint 4 (Days 5–6):** Coordinator, validator, bounded regeneration + deterministic terminal report, frontend.
- **Sprint 5 (Days 7–8):** Pinned demo, E2E, README/writeup, recording; Orbit only if core is stable.

## Tasks

### Task 1 — Fresh Repo Baseline + Provenance Guard — S — deps: none — [R10]
- **Test first:** `git log --format='%ai %ci'` shows **both author and commit** dates ≥ 2026-06-17 for every commit; `scripts/check_commit_window.py` fails on any earlier date.
- **Files:** `README.md`, `NOTICE.md`, `.gitignore`, `pyproject.toml`, `src/gdg_yorku_submission/__init__.py`, `tests/`, `scripts/check_commit_window.py`, `tests/test_commit_window.py`.
- **[R10]** `NOTICE.md` provenance table: component, source project/path, copied|adapted|new, license/ownership, date copied, notes; old Git history is NOT imported. Checker enforces author/commit dates only; provenance reviewed manually pre-submission.
- **Done when:** `pytest` runs; window checker passes; README + NOTICE state window + provenance.

### Task 2 — Core Schemas + Severity Mapping — M — deps: 1
- **Test first:** valid finding/status/report pass; invalid severity rejected; blocker/major/minor → critical/high/medium/low mapping table unit-tested; reporting-floor constant = `high`.
- **Files:** `src/gdg_yorku_submission/schemas.py`, `src/gdg_yorku_submission/severity.py`, `tests/test_schemas.py`, `tests/test_severity.py`.
- **Done when:** invalid severities fail; mapping is total and tested; floor defined in one place.

### Task 3 — Collision-Safe Deterministic Finding IDs — S — deps: 2 — [R8]
- **Test first:** same anchor → same ID across runs; different claim prose → same ID; different path/category → different ID; **two distinct same-category findings at the same file:line get DISTINCT stable IDs via occurrence ordinal**; tiebreaker order (sub-category → non-prose anchor → claim SHA) is unit-tested; findings with identical non-prose key are flagged for merge, not ordinaled.
- **Files:** `src/gdg_yorku_submission/finding_ids.py`, `tests/test_finding_ids.py`.
- **Done when:** all properties proven, including the collision and merge-vs-ordinal cases.

### Task 4 — FastAPI Walking Skeleton + Orchestrator Seam — M — deps: 1–3 — [R8]
- **Test first:** upload tiny zip → schema-valid report with stub findings fully accounted, no real LLM calls; in-process and (stub) ADK Orchestrator impls pass the **same** conformance test (`start_run`, `write_findings`, `read_state`, `run_specialist`, `finalize_ids`, `compile_report`); specialist failure writes `failed` and does not abort; ingestion failure aborts.
- **Files:** `src/gdg_yorku_submission/app.py`, `src/gdg_yorku_submission/orchestrator.py`, `src/gdg_yorku_submission/orchestration/__init__.py`, `tests/test_api_skeleton.py`, `tests/test_orchestrator_conformance.py`.
- **Done when:** E2E API test green with stubs; orchestration behind the seam; append-only state transitions.

### Task 5 — Hardened Zip Extraction — M — deps: 4 — [R1]
- **Test first:** zip-only accepted; `../evil.py` entry SKIPPED with `skipped_reason`; symlink/absolute-path entries SKIPPED; nested zip SKIPPED (not recursed); uncompressed-total / file-count / per-file / compressed caps ABORT the run; `.whl`/`.jar` fixtures pass with skipped entries logged; `.venv`/`*.db`/binaries skipped during ingestion and excluded from extraction and pre-flight scanning to preserve performance and prevent scanning noise (while gitignored files like `.env` are fully scanned).
- **Files:** `src/gdg_yorku_submission/ingest.py`, `tests/test_ingest.py`, `tests/fixtures/`.
- **Done when:** abort-vs-skip policy proven; manifest records included + skipped entries.

### Task 6 — Exposure-Model Prompt Corpus — M — deps: 5 — [R2][R5]
- **Test first:** file classified `prompt_exposed` / `ignored_by_root_gitignore` / `excluded_by_system` deterministically; root-gitignored file excluded from prompt corpus but present in full-scan manifest; `pathspec` `!` negation honored; same upload → identical classification across reruns; nested-gitignore documented unsupported; **[R5]** each text file wrapped as `CorpusFile` with original_text/redacted_text/line-count/map and an `evidence_ref`.
- **Files:** `src/gdg_yorku_submission/corpus.py`, `tests/test_corpus.py`, `README.md`.
- **Done when:** scan scope and prompt scope provably decoupled; original coordinates preserved.

### Task 7 — Secret Scanner + Redaction Invariant — L — deps: 5–6 — [R3]
- **Test first:** tracked-source synthetic secret → `high`; gitignored `.env` secret → `info`; raw secret absent from finding JSON; prompt corpus shows placeholder not raw secret; short-secret fingerprint is salted-hash-only (no last-4 leak); `GateFinding` always in `secret_scan_summary`; prompt-exposed high gate finding promotes to a `ReviewFinding{perspective: security}`; `RedactionContext` sanitizes a sample log line, exception, validator error, and trace fixture.
- **Files:** `src/gdg_yorku_submission/preflight/secrets.py`, `src/gdg_yorku_submission/preflight/redaction.py`, `tests/test_secret_preflight.py`.
- **Done when:** full-corpus scan, severity split, promotion, no raw-secret propagation, safe fingerprint all proven.

### Task 8 — Evidence-Plane Prompt Builder (nonced) — M — deps: 6–7
- **Test first:** "ignore prior instructions" in code/SPEC appears only inside evidence delimiters; trusted methodology stays separate; attacker text containing the literal delimiter cannot break out because the delimiter carries a per-run random nonce; redacted text only (no raw secrets) enters the prompt.
- **Files:** `src/gdg_yorku_submission/prompts/evidence_plane.py`, `tests/test_evidence_plane.py`.
- **Done when:** untrusted content is delimited, nonced, and redacted; break-out test passes.

### Task 9 — Source-of-Truth Discovery — M — deps: 8 — [R2]
- **Test first:** repo with `SPEC.md` selects it; README intent section selected **only** via heading allowlist (`## Spec`/`## Design`/`## Requirements`/`## Intent`); no allowlisted heading + no SPEC → `no_spec_found_conformance_skipped`; injection text in SPEC stays evidence-plane; selection reproducible across reruns.
- **Files:** `src/gdg_yorku_submission/correctness/sot.py`, `tests/test_sot_discovery.py`.
- **Done when:** sample SPEC discovered reliably; no-spec fallback explicit and accounted.

### Task 10 — Rewrite Correctness Methodology — S — deps: 9
- **Test first:** static test asserts no security/secret/dependency/TDD/Antigravity-PASS/FIX sections remain; asserts required schema fields named; asserts no-spec findings capped at `medium`.
- **Files:** `src/gdg_yorku_submission/correctness/methodology.md`, `tests/test_correctness_methodology.py`.
- **Done when:** rubric is correctness-only and schema-emitting.

### Task 11 — Deterministic Security Baseline Pass (Python AST) — M — deps: 5–8 — **[R6] always-on, before the debate**
- **Test first:** Python sample files trigger SQLi/`shell=True`/unsafe-deserialize/missing-auth/path-traversal/`verify=False` findings with correct mapped severities and original-coordinate locations; no LLM involved; perspective status `complete`; a non-Python file yields status `complete_limited` reason `no deterministic rules for <lang>` with metadata `unsupported_language_count`.
- **Files:** `src/gdg_yorku_submission/security/deterministic.py`, `tests/test_security_deterministic.py`.
- **Done when:** a complete, schema-valid, language-scoped security perspective exists with zero LLM dependency. **This is the always-on baseline.**

### Task 12 — Correctness Agent Adapter — L — deps: 8–10 — [R5][R7]
- **Test first:** fake Gemini client returning valid JSON → validated findings with original-coordinate evidence_refs; malformed JSON → `failed` status/retry; no-spec repo → skipped/accounted status; SoT/code loaded as evidence-plane, methodology as trusted instructions; budget lease acquired before call, acquisition failure → `failed:budget_exhausted`.
- **Files:** `src/gdg_yorku_submission/correctness/agent.py`, `src/gdg_yorku_submission/llm/gemini.py`, `src/gdg_yorku_submission/budget.py`, `tests/test_correctness_agent.py`.
- **Done when:** fake-client tests pass; manual Vertex smoke runnable.

### Task 13 — Coordinator Compiler — L — deps: 2, 4, 11, 12 — [R4][R8]
- **Test first:** Orchestrator ID-finalization runs before the coordinator and freezes IDs; fake output referencing only known IDs passes; invented ID fails; severity change fails; prose-severity mismatch fails; cross-perspective merge rejected; same-perspective/same-source merge carries `merged_from` and `max` severity; produces the canonical `ReviewReport` schema.
- **Files:** `src/gdg_yorku_submission/coordinator/agent.py`, `src/gdg_yorku_submission/coordinator/prompts.py`, `tests/test_coordinator_agent.py`.
- **Done when:** coordinator compiles fake specialist findings (correctness + deterministic security) into a `ReviewReport`. **At this point the full valid pipeline exists WITHOUT the debate.**

### Task 14 — Conservation Validator — L — deps: 13 — [R4][R5]
- **Test first:** report dropping a high finding rejected; every input ID Included/Merged/Omitted; merge severity = deterministic max (LLM value ignored); unknown omitted ID rejected; **evidence_ref citing a path/line outside the loaded corpus/SoT span rejected (syntactic existence check)**; deterministic severity counts; contested K-cap applies only below high floor, high/critical contested enumerated in full.
- **Files:** `src/gdg_yorku_submission/coordinator/validator.py`, `tests/test_report_validator.py`.
- **Done when:** validator-rejection cases triggerable from tests.

### Task 15 — Bounded Regeneration + Deterministic Terminal Report — M — deps: 14 — **[R7] universally reachable**
- **Test first:** invalid→valid on retry returns valid report; after R retries exhausted, terminal report ships; **terminal report ALSO ships on insufficient-budget and on coordinator error/timeout entry points**; terminal report is schema-valid (`merged=[]`, `omitted=[]`), includes every input finding verbatim, fully accounts, and uses zero LLM budget; retries counted against the budget.
- **Files:** `src/gdg_yorku_submission/orchestrator.py`, `src/gdg_yorku_submission/coordinator/terminal_report.py`, `tests/test_report_regeneration.py`.
- **Done when:** the pipeline cannot fail to emit a valid, fully-accounted report from any of the three entry points.

### Task 16 — Pinned Demo Sample — M — deps: 5–9, 11
- **Test first:** ingestion confirms `samples/driftstore` has a tracked secret, a gitignored `.env` secret, `SPEC.md` with a known divergence, and a Python deterministic-security-detectable issue; secret severity split confirmed; sample is a `.zip` fixture.
- **Files:** `samples/driftstore/{SPEC.md,.gitignore,.env,app.py,tests/}`, `samples/driftstore.zip`, `tests/test_demo_sample.py`.
- **Done when:** sample reliably triggers every intended finding through the LLM-free path.

### Task 17 — Frontend Report Viewer — M — deps: 4, 14 — [R4]
- **Test first:** HTML/JS test renders upload form + all `ReviewReport` sections from fixture JSON (perspective statuses, gate status, severity counts, high/critical header, findings, contested, secret_scan_summary, accounting ledger); no raw secret literals in rendered output.
- **Files:** `src/gdg_yorku_submission/static/{index.html,app.js,styles.css}`, `src/gdg_yorku_submission/app.py`.
- **Done when:** user can upload the sample and read the report in-browser.

### Task 18 — Out-of-Band Validator-Rejection Demo Hook (CLI-only) — S — deps: 14 — [R9]
- **Test first:** `python -m gdg_yorku_submission.demo_hooks drop-high samples/driftstore.zip` runs the validator against a deliberately corrupted in-memory report and prints validator errors; a test asserts the module is **not** imported by any FastAPI route and not reachable over HTTP.
- **Files:** `src/gdg_yorku_submission/demo_hooks.py` (clearly non-production), `tests/test_validator_demo_hook.py`, `docs/demo-script.md`.
- **Done when:** the rejection moment is reproducible on camera as an out-of-band integrity test; hook is unreachable from the production request path.

--- UPGRADES (cut without breaking the core) ---

### Task 19 — Debate Data Model — M — deps: 2 — [R4]
- **Test first:** every candidate resolves to `survived`/`defeated:{reason}`/`contested`; at-or-above-floor contested item reportable; contested K-cap applies **only below the high floor**; all high/critical contested items enumerated in full.
- **Files:** `src/gdg_yorku_submission/security/debate_schema.py`, `tests/test_debate_schema.py`.

### Task 20 — Port Crucible Debate Loop — L — deps: 19 — [R7]
- **Test first:** fake defender/challenger → deterministic rounds; stop fires on (delta<threshold AND finding-stability for N rounds) OR max-round/token cap; max-round cap stops non-convergence; `RunBudget`/`BudgetLease` token + separate-Claude caps enforced.
- **Files:** `src/gdg_yorku_submission/security/debate.py`, `src/gdg_yorku_submission/security/stop_condition.py`, `tests/test_debate_loop.py`.

### Task 21 — Security Debate Adapter — L — deps: 7, 8, 20 — [R7]
- **Test first:** survived candidate → schema-valid finding; raw secret evidence never in debate prompt; debate failure or `failed:budget_exhausted` → **falls back to the Task 11 baseline**, report still completes.
- **Files:** `src/gdg_yorku_submission/security/agent.py`, `src/gdg_yorku_submission/llm/claude.py`, `tests/test_security_agent.py`.
- **Day-4 decision:** if the debate is not emitting schema-valid survivors by end of Day 4, **stop** — the baseline already ships the security perspective; spend remaining time on coordinator/validator/demo, not on Orbit.

### Task 22 — Optional Orbit Blast-Radius — L — deps: 2, stable core
- **Test first:** fake Orbit client → downstream finding; missing config → `disabled` status, report still completes.
- **Files:** `src/gdg_yorku_submission/blast_radius/{agent.py,orbit_client.py}`, `tests/test_blast_radius.py`.
- Only after the entire core + demo is green; never on the critical path.

--- CLOSE-OUT ---

### Task 23 — End-to-End Tests — L — deps: 15, 16, 17 — [R3]
- **Test first:** sample through full pipeline (fake clients) asserts expected finding IDs + full accounting; **asserts raw synthetic secrets absent from all serialized output** (logs, API responses, report JSON, LLM payload fixtures, validator errors, trace artifacts); asserts terminal-report fallback path; asserts promoted secret is non-omittable.
- **Files:** `tests/test_e2e_sample_review.py`, `tests/fixtures/`.

### Task 24 — Real-LLM Smoke Script — M — deps: 12, 15, 16 — **[R10] deps changed (21 removed)**
- **Test first:** script runs in dry-run/fake mode with no credentials; if Task 21 exists, debate is gated behind `--with-debate`, else runs correctness + deterministic security + coordinator only.
- **Files:** `scripts/run_sample_review.py`, `tests/test_run_sample_script.py`.
- **Done when:** close-out smoke task ships even if the debate (Task 21) is cut on Day 4.

### Task 25 — README + One-Page Writeup + Provenance — M — deps: stable core — [R10]
- **Test first:** checklist — setup, run, architecture, Google-tech usage, ADK-seam note, supported-language list, provenance table (`NOTICE.md`), demo instructions, limitations, the validator/terminal-report guarantee.
- **Files:** `README.md`, `NOTICE.md`, `docs/one-page-writeup.md`, `docs/architecture.md`.

### Task 26 — Evidence + Recording Prep — M — deps: 17–25
- **Test first:** manual dry run from a clean checkout.
- **Files:** `evidence/{test-results.txt,demo-report.json,screenshots/}`, `docs/demo-script.md`.

## Suggested 8-Day Schedule (with slack)
- **Day 1:** Tasks 1–4 (repo+window guard, schemas+severity, collision-safe IDs, skeleton+seam).
- **Day 2:** Tasks 5–6 (hardened zip extraction, exposure-model corpus); start 7.
- **Day 3:** Finish 7; Tasks 8, 9, 10 (nonced evidence plane, SoT, methodology).
- **Day 4:** Task 11 (deterministic security baseline — **always-on**), Task 12 (correctness adapter). **Now a security perspective is guaranteed.** Begin debate upgrade (19–20) only if ahead; make the Day-4 cut decision.
- **Day 5:** Tasks 13, 14, 15 (coordinator, validator, bounded regeneration + terminal report). **Full valid pipeline complete without the debate.**
- **Day 6:** Tasks 16, 17, 18 (demo sample, frontend, out-of-band rejection hook). Layer debate (21) if the Day-4 upgrade was healthy.
- **Day 7:** Tasks 23, 24, 25 (E2E, smoke, docs). Orbit (22) **only** if everything above is green.
- **Day 8:** Task 26 (evidence + recording); buffer/fixes only; record; submit.

## Hard Priority Order
1. Walking skeleton → schema-valid report (behind orchestration seam).
2. Full-corpus secret scan, no raw-secret propagation, safe fingerprint.
3. Correctness agent vs untrusted SoT (nonced evidence plane, original coordinates).
4. **Always-on deterministic Python security baseline.**
5. Coordinator + conservation validator (incl. evidence existence) + **universally-reachable deterministic terminal report.**
6. Demo sample + out-of-band validator-rejection moment.
7. Debate upgrade (cut at Day-4 decision if not converging).
8. Frontend polish + writeup + provenance.
9. Orbit — only after all above are stable.