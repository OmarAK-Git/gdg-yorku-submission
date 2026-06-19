# Project Brief: GDG-YorkU Code Review

Multi-agent automated code-review system for the Google × GDG-on-Campus-York case competition.

## Core Mission
Accept a `.zip` repository upload and generate a single structured, actionable, and fully-accounted review report that developers can act on directly.

## High-Level Requirements
- **Multi-Agent Design**: At least two specialized review perspectives (Correctness and Security) and a coordinating synthesizer.
- **Google Tech Stack**: Built using FastAPI, Google ADK (with an in-process fallback option), Gemini, and Vertex AI.
- **Deterministic Security Baseline**: An always-on, LLM-free Python AST scanner as the base security perspective, optionally upgraded to a defender-challenger debate loop.
- **Correctness Perspective**: Validates code against discovered Source-of-Truth (SoT) files in the repo (such as `SPEC.md`, `DESIGN.md`, README headers).
- **Production Safeguards**:
  - Hardened zip extraction with aggregate limits and entry-skipping logic to prevent archive bombs.
  - Secret scanner pre-flight gate with salted hash fingerprints and system-wide raw secret redaction invariant.
  - Prompt-injection isolation using nonced delimiters.
  - Deterministic ID finalization to assign stable, collision-safe finding IDs.
  - Syntactic existence check for evidence coordinates.
  - Run budget guardrails (max tokens/costs) to limit Gemini and Claude usage.
- **Reliability Guarantee**: A deterministic validator combined with bounded regeneration and a fallback to a zero-LLM deterministic terminal report to ensure a valid report is always produced.

## Source of Truth
Authoritative specifications and plans reside in the [docs/](file:///c:/Users/oalan/gdg-yorku-submission/docs) directory:
- [Specification](file:///c:/Users/oalan/gdg-yorku-submission/docs/spec.md)
- [Implementation Plan](file:///c:/Users/oalan/gdg-yorku-submission/docs/plan.md)
