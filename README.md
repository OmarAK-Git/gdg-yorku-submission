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
