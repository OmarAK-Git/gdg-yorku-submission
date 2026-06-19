# Notice / Provenance Statement

All Git history in this repository starts ≥ 2026-06-17, conforming to the case competition rules. Reused logic is documented below.

## Provenance Table

| Component | Source Project/Path | Copied / Adapted / New | License/Ownership | Date Copied | Notes |
|---|---|---|---|---|---|
| Project Structure & Setup | None | New | MIT / GDG YorkU Team | 2026-06-18 | Initial project layout, CLI scripts, and test suite. |
| Core Schemas | None | Planned | MIT / GDG YorkU Team | *Planned* | Clean schemas for finding tracking and reports. |
| Ingestion & Zip Handling | None | Planned | MIT / GDG YorkU Team | *Planned* | Safe extractor with traversal guards. |
| Secret Scanner | Tumbler logic | Planned (Adapted) | MIT | *Planned* | Ported regex patterns and validation rules from Tumbler. |
| Redaction Context | None | Planned | MIT / GDG YorkU Team | *Planned* | Salted hash and placeholder logic. |
| Correctness Adapter | None | Planned | MIT / GDG YorkU Team | *Planned* | Grounding adapter for Gemini correctness validation. |
| Deterministic AST security | None | Planned | MIT / GDG YorkU Team | *Planned* | Custom Python AST rules (SQLi, deserialization, etc.) |
| Debate Loop | Crucible | Planned (Adapted) | MIT | *Planned* | Ported adversarial defender/challenger loop structure. |
| Coordinator & Validator | None | Planned | MIT / GDG YorkU Team | *Planned* | Validation invariants and terminal report fallback. |
