# Document 1 — Specification (Critic-Finalized)

> Reviewer: Dr. Rivera (Critic / Red Team). This is the finalized spec. Repair-brief root-cause fixes **R1–R10** (covering gaps 1–22) are incorporated inline and tagged where they land. Agreement with the peer draft was earned, not assumed.

## Goal

Build a multi-agent automated code-review system for the Google × GDG-on-Campus-York case competition. It accepts a **`.zip` upload** and returns one structured, actionable, fully-accounted review report a developer can act on directly.

The system must demonstrate:
- At least two specialized review perspectives plus a coordinating synthesizer (rubric requirement).
- Meaningful use of Google tech: Gemini, Vertex AI, ADK.
- Production-minded safeguards: prompt-injection isolation, system-wide secret redaction, schema validation, and report traceability (conservation accounting).
- A credible 8-day solo build path with an always-valid degraded mode.

Primary V1 perspectives:
- **Correctness agent** — Vertex/Gemini; checks code against the uploaded repo's own Source-of-Truth when one exists.
- **Security/assurance** — an always-on **deterministic Python-AST security baseline**, upgraded when time allows to a Gemini-defender vs Claude-challenger adversarial debate.

Optional V1.1 perspective:
- **Blast-radius agent** — Orbit/GitLab Knowledge Graph cross-repo impact.

## Non-Goals

- No general static-analysis platform; no full semantic verification.
- The coordinator never creates, suppresses, or re-severities findings.
- Never fabricate a spec when the repo has none.
- Never send a raw secret to any LLM context, report, log, trace, validator error, or frontend payload.
- Orbit is never a required demo dependency.
- No replay-fixture subsystem in V1 (the demo is a re-shootable recording).
- The old PASS/FIX + Antigravity-prompt contract is **not** the output; output is structured findings + a consolidated report.
- **[R1]** Folder upload is **not** a V1 backend mode — folders are zipped client-side or deferred to V1.1.
- **[R2]** V1 does **not** consult the Git index for tracked/untracked status; exposure is computed deterministically from ingestion filters + root `.gitignore`.

## Architecture

### High-Level Flow
1. User uploads a **`.zip`** via the frontend. **[R1]**
2. Backend safely extracts and normalizes into a run workspace under aggregate caps and a per-entry skip policy.
3. Pre-flight gate scans the **full** extracted corpus for secrets, including gitignored files.
4. Prompt-corpus builder applies deterministic exposure rules and redacts any prompt-exposed secrets **before** any model context exists.
5. Correctness agent reviews the prompt-exposed corpus against discovered Source-of-Truth evidence.
6. Deterministic security baseline reviews the sanitized corpus + pre-flight secret evidence (always on); the debate runs as an upgrade if enabled.
7. Optional blast-radius agent runs if enabled and configured.
8. **[R8]** After all perspective statuses are complete/failed, the Orchestrator runs an **ID-finalization stage** (freeze deterministic IDs), then specialists' findings + perspective statuses are in shared state.
9. Gemini coordinator compiles findings under strict constraints.
10. Deterministic validator accepts or rejects; rejected reports are regenerated with errors, bounded by a retry cap, then fall back to a **deterministic terminal report**.
11. Frontend displays the accepted report, statuses, secret-scan summary, and accounting ledger.

**Orchestration abstraction seam.** ADK is new and a single point of failure on an 8-day clock. Orchestration is accessed only through a thin internal `Orchestrator` interface (start run, run specialists, read/write shared state, finalize IDs, compile report). ADK is the default implementation; a ~40-line plain-Python in-process implementation of the same interface is the documented escape hatch. **[R8]** Both implementations pass identical conformance tests. Shared-state objects are plain Pydantic models, not ADK-native types, so they survive a backend swap.

## Key Components

### 1. Upload and Corpus Ingestion **[R1]**
Input modes: V1 required **`.zip`** upload; V1.1 optional folder/pasted file/diff; not-V1 live PR link.

**Aggregate caps (abort the run if exceeded mid-stream):**
- Max **compressed** bytes: 50MB.
- Max **uncompressed** total bytes (e.g. 500MB).
- Max file count.
- Max per-file bytes.

**Per-entry skip policy (skip, never abort):** inner/nested archives, symlink entries, absolute-path entries, and path-traversal entries (normalized resolved path escaping the workspace root) are **SKIPPED** — excluded from the workspace but recorded in the manifest with a `skipped_reason`. The run aborts **only** when an aggregate cap is exceeded.
- System excludes (recorded, not scanned for review): `.venv`/virtualenvs, binary blobs, `*.db`, build artifacts, large generated files.
- The full-corpus **secret scan still reaches all included files**, including `.env`.

**Exposure model (deterministic, no Git index) [R2]:** classify every included file as exactly one of:
- `prompt_exposed` = included by ingestion filters AND not matched by root `.gitignore`.
- `ignored_by_root_gitignore` = matched by root `.gitignore`.
- `excluded_by_system` = `.venv`, binaries, databases, build artifacts, size exclusions.

Root `.gitignore` is parsed with `pathspec` GitWildMatch including `!` negation; nested `.gitignore` is V1.1 with documented root-only V1 semantics.

**Important distinction:** secret-scan scope = full extracted corpus (incl. gitignored). LLM prompt scope = `prompt_exposed`, secret-redacted corpus.

**Original-coordinate corpus model [R5]:** every ingested text file is wrapped as `CorpusFile{normalized_path, original_text, redacted_text, original_line_count, redacted_to_original_line_map, evidence_ref}`. Prompts may use `redacted_text` only, but must preserve line count or carry the map so every `location` resolves to the developer's original line numbers.

### 2. Pre-Flight Secret Gate **[R3]**
Deterministic; not a review perspective.
- Scans all included files incl. `.env`, `*.pem`, gitignored files.
- Detects secrets using ported Tumbler logic; redacts before any prompt is built.
- Emits `GateFinding` objects that **always** appear in the report's `secret_scan_summary`.
- Tracked under a separate `GateStatus` (not `PerspectiveStatus`, which covers review perspectives only).

**Gate→review promotion:** a `prompt_exposed` gate finding at `high`/`critical` is converted by the security perspective into a `ReviewFinding{source_agent: preflight_secret_gate, perspective: security}` and **enters coordinator conservation accounting** (non-omittable). Ignored / system-excluded gate findings stay advisory unless promoted.

**Secret propagation invariant (system-wide, not a prompt filter):** raw secret values never enter prompts, debate evidence, reports, logs, traces, validator errors, frontend payloads, or test assertions — except the intentionally synthetic secrets in the pinned demo repo. All corpus-derived serialization passes through a single `RedactionContext` that owns spans, placeholders, and fingerprints. Raw request/body logging is disabled; exception messages, validator errors, and LLM request/response traces are sanitized before persistence/return.

**Fingerprint must not leak short secrets.** Fingerprint = a truncated **salted hash** (per-run salt). A last-4 substring is permitted **only** for values ≥20 chars where 4 trailing chars are non-identifying; otherwise hash-only.

**Severity policy (exposure-aware):** prompt-exposed source secret = `high` (critical-credential criteria → `critical`); ignored/system-excluded secret = `info`/advisory. Exposure status is set from the deterministic exposure model, not the Git index.

Gate finding fields: `id`, `source_agent: preflight_secret_gate`, `perspective: security`, `severity`, `location`, `claim`, `evidence_ref`, `secret_type`, `fingerprint`, `exposure_status`.

### 3. Source-of-Truth (SoT) Discovery **[R2]**
The conformance target is the uploaded project's own spec, not the correctness methodology doc.
Discovery order: root `SPEC.md` → root `DESIGN.md` → README intent sections (selected **only** via a fixed heading allowlist: `## Spec`, `## Design`, `## Requirements`, `## Intent`) → conventional `docs/SPEC.md` if cheap. Absent → no-spec fallback.

Trust boundary: SoT files are **untrusted repo content**, loaded as evidence-plane data behind nonced delimiters, never in the trusted instruction channel. Injection text inside SPEC/README is content to analyze, not instructions.

No-spec fallback: never invent a spec. Either infer limited intent from docstrings/signatures/filenames and check internal logic-consistency only, or emit accounted status `no_spec_found_conformance_skipped`. No-spec logic-consistency findings are **capped at `medium`** severity and must cite concrete in-code evidence (the hallucination surface is highest here).

Demo requirement: pinned sample ships its own `SPEC.md` with known, direction-neutral divergences.

### 4. Correctness Agent
Vertex AI Gemini, grounded against the discovered SoT evidence-plane corpus. **Clarify "grounded":** the SoT is passed as evidence-plane context in the prompt; this is **NOT** Vertex Search/RAG indexing (which would add an indexing dependency and latency the window can't afford). "Grounded" = the agent must cite SoT line references for every divergence finding.

Operating rubric: a rewritten correctness-only methodology (strip secret hygiene, security blockers, evidence/dependency handling, TDD); keep intent extraction, spec-code divergence, traceability, logic-vs-spec. Emit schema-valid findings only; divergences are direction-neutral ("code and SPEC.md disagree at X", not "code is wrong"). **[R5]** All `location`/`evidence_ref` fields use original-file coordinates (`file:path#line_start-line_end`).

### 5. Security/Assurance Node
**Ordering: deterministic baseline FIRST, debate as a strict upgrade.** A debate that slips must never leave the system with no security perspective — that is an unacceptable single point of failure for a 35%-architecture / 25%-reliability rubric.

**Deterministic baseline pass [R6] — V1 is Python-only, high-precision AST/token rules:**
- SQLi = DB execute call receiving an f-string/concat/`format` with non-literal input.
- `shell=True` = subprocess/os call with `shell=True` and a non-literal command.
- Unsafe deserialization = `pickle.loads/load` or `yaml.load` without `SafeLoader` on non-literal/input data.
- Missing-auth write route = Flask/FastAPI POST/PUT/PATCH/DELETE lacking a configured auth decorator/dependency.
- Path traversal = `open`/path-join on request input without a normalize-and-root check.
- `verify=False` = requests call with literal `verify=False`.

Detect corpus language(s) from the manifest. Languages with no ported rules → security status `complete_limited` with reason `no deterministic rules for <lang>` (**never** `complete`); set metadata `unsupported_language_count`. Supported languages documented in README. A non-Python upload **never** presents an empty result as a full security pass.

**Debate upgrade:** Gemini defender ("this ships — API consistency, dependency hygiene, test posture") vs Claude challenger ("not yet — vulns, edge cases, rate-limiting, scope creep"). Reuse Crucible/GDG-YorkU Code Review loop, personas, scoring.

**Stop condition (additive, not a replacement):** retain Crucible's tuned delta score; terminate when delta < threshold **AND** no new at-or-above-floor candidate for N rounds, **OR** when max rounds / token budget is reached. This preserves the human's already-tuned asset (reopening it is the most expensive mistake available) while adding review-specific convergence.

**Debate ledger:** every challenger candidate resolves to `survived` | `defeated:{closed_reason}` | `contested`. At-or-above-floor `defeated`/`contested` items remain visible in the report as **contested** (never silently dropped).

**Contested cap [R4]:** the K cap applies **only below the high floor**. All `high`/`critical` contested items are enumerated in full and exempt from the cap; if budget is exceeded the list is noted as high-only.

Output: deterministic code derives the debate result object from the transcript + structured ledger; neither debater authors the verdict.

**Cost guard [R7]:** a `RunBudget{max_total_tokens, max_gemini_tokens, max_claude_tokens, max_llm_calls, max_cost_usd, used_*}` plus `BudgetLease(component, estimated_tokens, provider)`. Every LLM component acquires a lease before calling; the **separate Claude/Anthropic budget cap** (separate billing) is enforced via `max_claude_tokens`. Budget reserves one coordinator attempt; the coordinator regeneration loop counts against the budget. A cheap-model/reduced-round dev mode exists.

### 6. Optional Blast-Radius Agent (Orbit)
Query prefetched GitLab Knowledge Graph by definition/imported-symbol with a health check. Optional, toggleable. If unavailable, status is explicitly `disabled`/`unconfigured`/`unavailable` and the other two perspectives still produce a complete report. Orbit is a true cut: it ships only if the entire core path is stable and tested, and is never on the critical path or the schedule before Day 7.

### 7. Shared State and Finding Schema
All specialists write schema-validated objects to shared state via the `Orchestrator` seam.

```json
{
  "id": "string",
  "source_agent": "preflight_secret_gate|correctness_agent|security_debate|security_deterministic|blast_radius_agent",
  "perspective": "preflight|correctness|security|blast_radius",
  "severity": "critical|high|medium|low|info",
  "location": { "path": "string", "line_start": 1, "line_end": 1 },
  "claim": "string",
  "evidence_ref": ["file:path#line_start-line_end"],
  "status": "active|contested|advisory",
  "metadata": {}
}
```

**Severity-vocabulary reconciliation.** The old methodology speaks blocker/major/minor; the new schema is critical/high/medium/low/info. Canonical mapping, applied at every emit point: blocker→`critical`, security-blocker→`high` (reserve `critical` for active credential exposure / confirmed exploit), major→`medium`, minor→`low`, observational/hygiene→`info`. **Reporting floor = `high`.** Any finding at `high` or `critical` is non-omittable.

**ID rule — deterministic, collision-safe, Orchestrator-finalized [R8].** IDs derive from deterministic anchors (hash of `source_agent + normalized_path + line_start + rule_or_category + stable_symbol_if_available`), never from LLM prose. Two *distinct* findings of the same category at the same `file:line` would hash identically and silently collapse — a hidden omission. Fix: an Orchestrator-owned **ID-finalization stage** runs after all perspective statuses are complete/failed and before the coordinator: collect all provisional findings, group by anchor, sort by a prose-free key, assign a per-anchor occurrence **ordinal** (0,1,2…), then freeze IDs. Ordinal tiebreaker order = (sub-rule/sub-category enum if emitted) → normalized non-prose evidence anchor (matched token offset / AST node id) → SHA of full claim last. Findings collapsing to an identical **non-prose** key MUST be merged, not ordinaled. ID stability is guaranteed for detector-backed findings; LLM-authored findings without a non-prose discriminator fall back to claim-hash ordinals with documented best-effort stability.

Perspective status (review perspectives only):
```json
{ "perspective": "correctness|security|blast_radius", "status": "complete|complete_limited|skipped|disabled|unavailable|failed", "reason": "string", "finding_ids": ["string"] }
```
Gate status is a separate `GateStatus` object.

### 8. Coordinator
Gemini, schema-locked; a constrained compiler, not a reviewer.
Allowed: order, group, dedupe within validator rules, write prose tied to existing IDs, summarize statuses.
Forbidden: invent findings, add absent claims, change severity, overturn debate verdicts, drop high/critical, or state a prose severity differing from the structured field.

**Merge rules [R4]:** merges restricted to the **same `perspective` AND same `source_agent`**; cross-perspective findings may be grouped/ordered but **never merged**. Merged severity = deterministic `max` of constituents. `merged_from:[ids]` is required on any merged item. Merge cardinality is capped (V1.1 enforcement).

**V1 validator invariants (deterministic):** schema validity; stable-ID attribution; conservation accounting (every input ID is Included | Merged | Omitted); high/critical non-omission; no severity downgrade on merge; no unknown IDs; no severities/claims absent from inputs; **[R5]** evidence-coordinate existence — reject any finding whose `evidence_ref` cites a path/line outside the actually-loaded corpus/SoT span (syntactic existence check, not semantic).
**V1.1 invariants:** merge-cardinality cap, evidence-ref carry-forward checks, deterministic duplicate/superseded validation, same-perspective-merge restriction enforcement upgrades.

**Bounded regeneration + deterministic terminal report [R7].** Cap regeneration at R attempts (e.g. 2). The deterministic terminal report — every input finding Included verbatim, ordered by severity then path, no merges, empty omissions, templated prose — is emitted on **ANY** of: R attempts exhausted; insufficient remaining budget for a coordinator call; coordinator call error/timeout. It requires **zero LLM budget** and is valid by construction and fully accounted. The pipeline therefore *cannot* fail to produce a valid report — a first-class reliability property for the 25% demo-reliability rubric.

### 9. Final Report Shape **[R4]**
```
ReviewReport{
  run_metadata, corpus_summary, perspective_statuses, gate_status,
  severity_counts, high_critical_findings,
  findings:[ReportFinding{id, severity, location, claim, evidence_ref,
                          source_agent, perspective, status,
                          recommended_next_action, merged_from[]}],
  contested_items:[...],
  secret_scan_summary,   // no raw secrets, ever
  accounting_ledger:{ included:[id],
                      merged:[{output_id, input_ids}],
                      omitted:[{id, reason}],
                      contested:[id] }, // 4th bucket to track contested findings distinctly from omitted ones
  validator_warnings:[]
}
```
The high/critical header is deterministically rendered so narration can't bury a finding. The terminal report uses this exact schema with `merged=[]`, `omitted=[]`, `contested=[]`, and every input finding verbatim.

## Tech Stack
Backend: Python, FastAPI, Google ADK (behind the `Orchestrator` seam), Pydantic.
Frontend: existing Tumbler vanilla HTML/CSS/JS scaffold; upload, status panel, report viewer, ledger.
LLM/AI: Vertex AI Gemini (correctness + coordinator + defender); Claude API (challenger).
Deterministic tooling: ported Tumbler secret scanner; `pathspec` GitWildMatch gitignore parser; hardened zip extraction; Python `ast`-based security rules; Pydantic/JSON-schema validation.
Optional: Orbit/GitLab Knowledge Graph API; Crucible SSE streaming for live debate visibility.

## Key Design Decisions and Rationale
- **Zip-only ingestion with aggregate caps + per-entry skip [R1]** — a compressed cap alone does not stop zip bombs; skipping bad entries (not aborting) keeps real-world `.whl`/`.jar` uploads reviewable.
- **Scan full corpus, prompt only the exposed corpus** — secrets live in ignored files; ignored files shouldn't enter model context.
- **Deterministic exposure model, no Git index [R2]** — uploads aren't git repos; reproducible classification across reruns.
- **Raw secrets never enter any sink** — a reviewer that echoes a secret creates the incident; redaction is a system-wide invariant.
- **SoT from the uploaded repo, treated as untrusted** — methodology is *how* to review; the repo's own spec is *what* to review; a malicious SPEC.md must not steer the agent.
- **Direction-neutral divergences** — the spec may be stale; the developer adjudicates.
- **Deterministic security baseline before the debate** — guarantees a security perspective regardless of debate fate.
- **Additive delta + finding-stability stop** — preserves the tuned Crucible asset instead of reopening the hardest solved problem.
- **Orchestrator-finalized collision-safe IDs [R8]** — prevents hidden omissions from co-located findings while keeping IDs prose-free and stable.
- **Deterministic validator + universally reachable terminal report [R7]** — turns the highest-risk failure into a demonstrable guarantee and removes the possibility of producing no report.
- **Orchestration seam over ADK** — uses ADK for the rubric without making an immature SDK a single point of failure.
- **No replay-fixture mode in V1** — validator-rejection is a stronger, rubric-aligned demo moment.

## Acceptance Criteria
### Functional
- Upload `.zip` ≤50MB compressed; extraction aborts on uncompressed/file-count bombs, and skips (logging `skipped_reason`) traversal/symlink/absolute/nested-archive entries; `.whl`/`.jar` fixtures pass with skipped entries logged.
- Secret scanner scans full corpus incl. gitignored files; prompt builder excludes gitignored files; raw secrets never appear in prompts/reports/frontend/logs/validator errors/traces (asserted by test against synthetic literals).
- Prompt-exposed high/critical secret is promoted into conservation accounting and is non-omittable.
- Same upload yields identical exposure classification across reruns; `!` negation honored; README SoT selection reproducible via heading allowlist.
- Correctness agent uses the repo's own SoT when present; emits explicit `no_spec_found_conformance_skipped` otherwise; no-spec findings capped at `medium`.
- Security perspective always produces schema-valid findings (Python baseline guaranteed; debate when enabled); non-Python upload yields `complete_limited`, never empty `complete`.
- All `location`/`evidence_ref` use original-file coordinates; out-of-range citations are rejected by the validator.
- Coordinator produces a schema-valid report; validator rejects any report dropping a high/critical finding; every input ID is accounted for; merges are same-perspective/same-source with `max` severity.
- Terminal report ships on regeneration exhaustion, budget exhaustion, or coordinator error — valid and fully accounted, zero LLM calls.
- Severity enum mapping applied uniformly; floor = high.
- Finding IDs are stable across reruns and distinct for co-located same-category findings.
- Optional Orbit failure never blocks report generation.

### Demo **[R9]**
Pinned sample (`samples/driftstore`) ships: `SPEC.md` with a known divergence; a tracked file with a synthetic hardcoded secret; a gitignored `.env` with a synthetic secret; a Python security issue for the baseline/debate. The demo has two segments:
- **Segment A (live upload):** upload → secret-scan severity split → correctness divergence → security finding → coordinator conservation ledger → final accepted report.
- **Segment B (out-of-band integrity test):** a separate CLI invocation (`python -m gdg_yorku_submission.demo_hooks drop-high ...`) runs the validator against a deliberately corrupted in-memory report and prints the rejection. This hook MUST NOT be reachable over HTTP.

### Deliverables
Public repo, all commits in-window (**author and commit dates** ≥ 2026-06-17); README + `NOTICE.md` provenance table; recorded end-to-end demo; one-page rubric-aligned writeup.

## Risks and Mitigations
- **Debate consumes too much time** → deterministic baseline already shipped; debate is a pure upgrade; Day-4 decision is "layer debate or stop," never "build a security perspective from scratch."
- **Coordinator drops/weakens findings** → deterministic validator + bounded regeneration + universally-reachable terminal report; demo the rejection.
- **Secret leakage via logs/reports/fingerprint/traces/validator errors** → central `RedactionContext`, no raw-secret schema field, hash-only fingerprint for short secrets, tests asserting synthetic strings never appear in any sink.
- **Prompt injection via SPEC.md/code** → evidence-plane delimiters with a **per-run random nonce** so attacker-supplied delimiter strings cannot break out; tests with malicious SPEC content.
- **Archive bombs / traversal / symlinks** → uncompressed+count+per-file caps abort; bad entries skipped with reason.
- **Hallucinated citations** → original-coordinate evidence + syntactic existence validation.
- **ADK immaturity** → `Orchestrator` seam + plain-Python fallback passing identical conformance tests.
- **Gitignore semantics** → root-only V1 via `pathspec`, nested documented as V1.1.
- **Orbit instability** → optional, clean disabled status, true cut.
- **Budget overrun** → `RunBudget` + leases, separate Claude cap, one reserved coordinator attempt, cheap dev mode, cached sample uploads.
- **Commit-window / provenance disqualification** → fresh repo; copy reused code as *new* in-window commits (do NOT cherry-pick/rebase preserving original author dates); verify with `git log --format='%ai %ci'`; `NOTICE.md` documents reuse as in-window engineering.
- **Zero-slack solo schedule (newborn at home)** → Orbit dropped from the critical path; Day 8 reserved for recording + fixes only; the always-valid degraded path means an unfinished debate still yields a submittable system.