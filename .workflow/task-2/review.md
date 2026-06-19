# Review

## Spec compliance review

- The severity mapping satisfies all mapping conditions (e.g. blocker -> critical, major -> medium, minor -> low, observational/hygiene -> info).
- High reporting floor constant is defined at `severity.py` as `SEVERITY_FLOOR = Severity.HIGH`.
- Standard structures for `Finding`, `ReportFinding`, `GateFinding`, and `ReviewReport` are defined using Pydantic V2 as requested.
- Overloaded custom comparison operators for `Severity` enum ensure that ordering works correctly and prevents naive string comparisons from passing. Coerces raw strings (e.g. `Severity.MEDIUM >= "high"`) before comparing to prevent lexicographical fallback.
- Aliased `ReviewFinding = Finding` to match pre-coordinator specialist finding specifications written to the shared state.

## Code quality review

- Modules use clean Pydantic V2 fields and validators (using V2-compatible `@field_validator` and `@model_validator` APIs).
- Type hints are fully configured for all schemas.
- Configured V2 models with `extra="forbid"` to ensure that unknown/mistyped fields raise a `ValidationError` rather than silently discarding data.
- Added comments highlighting that semantic conservation is coordinator/validator-enforced, not schema-enforced, aligning with boundaries.

## Risk review

- Schema constraints prevent negative severity counts, invalid line number ranges, empty fingerprints/secret_type, and invalid exposure status strings, preventing corrupt reports downstream.

## Human review notes

- All tests run and pass without warnings. Added negative tests to attack all load-bearing invariants.
