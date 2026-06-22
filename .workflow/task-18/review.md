# Review - Task 18

## Spec compliance review
- Built out-of-band CLI tool `demo_hooks.py` with `drop-high`, `corrupt-location`, `corrupt-evidence-ref`, and `leak-secret` action subcommands.
- Verified that `drop-high` triggers validator rejection for high-severity omission.
- Verified that `corrupt-location` and `corrupt-evidence-ref` trigger coordinate check rejections independently.
- Verified that the `leak-secret` action demonstrates the redaction invariant holding on the serialized production report surface without manual demo-side scrubbing or metadata fabrication.
- Tested complete isolation from HTTP routes and production code by checking AST imports in `tests/test_validator_demo_hook.py`.

## Code quality review
- Clean separation of the non-production `demo_hooks.py` script.
- Subprocess and direct execution tests are robust and cover CLI argument parsing and correct exit codes.
- Removed unused imports `copy` in `demo_hooks.py` and `os` in `test_validator_demo_hook.py`.
- Checked `pyproject.toml` to ensure no console script entry points are registered for `demo_hooks`.
- Loud syntax error checks implemented in the isolation test suite (no silent skips on parse errors).

## Risk review
- Zero risk to production routes or web payloads since the demo hook is completely out-of-band and verified isolated.

## Human review notes
- Rejections are extremely readable and clearly list exact validator violations.
- In production, these validation errors would trigger warning logs and lead to terminal fallback compilation instead of aborting.
- The `leak-secret` action now properly tests the corpus redaction layer and asserts on the actual unmodified serialized JSON output.
