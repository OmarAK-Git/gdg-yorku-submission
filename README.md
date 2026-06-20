# GDG-YorkU Code Review

GDG-YorkU Code Review is a multi-agent automated code-review system developed for the Google × GDG-on-Campus-York case competition. It accepts a `.zip` repository upload and returns a structured, actionable, and fully-accounted review report.

## Commit Window & Provenance
- **Allowed Commit Window**: ≥ 2026-06-17. Checked automatically via `scripts/check_commit_window.py`.
- **Provenance Statement**: Reused/adapted components (e.g. from Tumbler or Crucible) are documented in [NOTICE.md](file:///c:/Users/oalan/gdg-yorku-submission/NOTICE.md).

## Key Features
- **Multi-Perspective Review**: Combines a correctness review (Gemini API) and an always-on deterministic Python-AST security scanner (upgradeable to defender/challenger debate).
- **Orchestration Seam**: Google ADK wrapper abstraction.
- **Safety Invariants**: Delimiter nonces, system-wide secret redaction, salted hash fingerprints.
- **Traceability Ledger**: Full conservation accounting (no silent finding drops by the LLM).
- **Deterministic Terminal Report**: Universal reliability fallback.

## Supported AST Security Rules
The deterministic security baseline scanner implements 6 high-precision Python AST checkers:
1. **SQL Injection (SQLi)**: Flags DB `execute`/`executemany` calls receiving non-literal queries built via f-strings, concatenation, or format calls.
2. **Command Injection (`shell=True`)**: Flags subprocess calls containing `shell=True` with non-literal commands, or os calls with non-literal arguments.
3. **Unsafe Deserialization**: Flags `pickle.load`/`loads` or `yaml.load` on non-literal/untrusted data (unless `yaml.load` specifies `Loader=yaml.SafeLoader` or similar).
4. **Missing Authorization**: Flags Flask/FastAPI POST/PUT/PATCH/DELETE write routes lacking authorization decorators or dependency injections. The scanner matches standard authentication/authorization keywords in decorators and dependencies (case-insensitive substring check):
   - `auth`, `login`, `jwt`, `session`, `permission`, `require`, `guard`, `protect`, `admin`, `role`, `user`.
5. **Path Traversal**: Tracks input parameters and `request` references in route functions, flags calls to `open`, `Path`, `os.path.join`, and `joinpath` using untrusted variables without a prior normalization/validation check (`resolve`, `abspath`, `realpath`, `startswith`, or `".."` checks).
6. **Disabled SSL Verification (`verify=False`)**: Flags `requests`/`httpx` HTTP calls containing keyword argument `verify=False`.

## Quick Start & Installation

### Setup Environment
```bash
# Clone the repository and navigate into it
cd gdg-yorku-submission

# Create a virtual environment
python -m venv .venv
source .venv/Scripts/activate

# Install dependencies
pip install -e ".[dev]"
```

### Running Tests
To run all baseline unit tests:
```bash
pytest
```

### Running Commit Window Checker
To verify git log compliance:
```bash
python scripts/check_commit_window.py
```
