# Review - Task 11

## Spec compliance review
- Deterministic Python-AST checker baseline implemented as the primary security specialist, ensuring it is always active.
- SQL Injection checker detects execute/executemany/execute_async using f-string, concat (+), or format calls with non-literal arguments.
- `shell=True` checker detects subprocess calls with `shell=True` and non-literal commands, as well as `os.system`/`os.popen` on non-literal inputs.
- Unsafe deserialization detects pickle loads/load and yaml.load on non-literal data without SafeLoader.
- Missing authorization detects POST/PUT/PATCH/DELETE endpoints that don't have auth decorators or auth dependency defaults.
- Path traversal detects open/join/Path on parameters or request attributes without resolve/realpath/abspath/startswith/.. checks.
- `verify=False` checker detects HTTP requests with verify=False.
- Language detection successfully inspects extensions and flags unsupported languages, setting the security status to `complete_limited` and updating `unsupported_language_count` in metadata.

## Code quality review
- All checkers are written using warning-free type checks (checking `type(node).__name__`) to avoid raising `DeprecationWarning` under pytest's strict warning-as-error configuration.
- The orchestrator interface was updated cleanly to allow returning custom statuses/reasons, remaining fully backwards-compatible with all existing list-returning lambdas and stubs.

## Risk review
- Gracefully handles `SyntaxError` (including `IndentationError`) on a per-file basis so a malformed file doesn't abort the entire code review scan.
- Clean separation between core checkers and E2E API integrations.

## Human review notes
- Static checkers do not perform full data-flow or points-to analysis. Code that uses custom wrappers around DB queries or indirect command executions will not be caught, which is standard for high-precision deterministic baseline tools.
