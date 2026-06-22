# Review - Task 19

## Spec compliance review
- Designed and implemented robust Pydantic schemas representing debate rounds and resolved/contested debate outcomes under `src/gdg_yorku_submission/security/debate_schema.py`.
- Formulated the `DebateCandidate` schema, enforcing the invariant that a `defeated` candidate must carry a non-empty `closed_reason` string (and conversely, survived/contested candidates must not have one).
- Built high-fidelity helper logic inside `DebateLedger` to correctly partition candidates:
  - `validate_completeness()` raises `ValueError` if any candidate remains unresolved (resolution=None) at the ledger boundary.
  - `get_survived()` returns findings that survived the debate with status updated to `"active"`.
  - `get_defeated()` returns defeated candidates.
  - `get_contested()` returns contested findings with status updated to `"contested"`. High/critical severity findings that were defeated are correctly preserved/promoted as contested instead of being silently dropped, and their closed reasons are threaded into `metadata["debate_closed_reason"]`.
  - `get_contested_with_kcap(k)` applies K-cap checks to below-floor contested findings, sorting them by rank and returning a `high_only_notice` boolean indicating if truncation occurred.
  - `get_omitted()` returns details (id and reason) of defeated findings that are below the floor (not high/critical) to be mapped to the omitted ledger.
- Exported all models cleanly from the `security` module in `src/gdg_yorku_submission/security/__init__.py`.

## Code quality review
- All models use Pydantic V2 configuration (`extra="forbid"`) to prevent extra arguments and avoid undocumented schema pollution.
- Validation checks are clean, using `@field_validator` and `@model_validator` correctly.
- Test coverage is 100% for all models and validation rules, including property-based tests verifying partition conservation, utilizing pytest assertions.

## Risk review
- Adding these schemas has zero impact on the existing non-debate review pipelines, as they are fully isolated inside `debate_schema.py` and exported cleanly.
- The schemas conform to standard Pydantic models used by the rest of the application.

## Human review notes
- The promotion of high/critical defeated findings to contested is a robust defense against silent omissions during debate, complying with the requirement that "at-or-above-floor defeated/contested items remain visible in the report as contested (never silently dropped)".
