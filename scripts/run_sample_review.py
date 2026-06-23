#!/usr/bin/env python3
"""
scripts/run_sample_review.py

A live run wrapper script for dry-run or actual integration runs.
Executes the full review pipeline on a target repository zip.

Usage:
    python scripts/run_sample_review.py --zip samples/driftstore.zip --orchestrator adk --with-debate
"""
import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Add src/ to Python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Load environment variables from a local .env file if present, so credentials
# and config (GOOGLE_CLOUD_PROJECT, model/effort overrides, run-mode flags) are
# picked up without requiring the caller to export them. Shell-exported vars win
# (load_dotenv does not override existing env vars).
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from gdg_yorku_submission.ingestion import HardenedZipExtractor, IngestionError
from gdg_yorku_submission.corpus import build_corpus
from gdg_yorku_submission.preflight.secrets import run_secret_scan
from gdg_yorku_submission.orchestrator import InProcessOrchestrator, AdkOrchestrator
from gdg_yorku_submission.security import make_security_specialist
from gdg_yorku_submission.correctness.agent import make_correctness_specialist
from gdg_yorku_submission.blast_radius import make_blast_radius_specialist


async def run_review(
    zip_path: Path,
    orchestrator_type: str,
    real_llm: bool,
    with_debate: bool,
    output_path: str = None
) -> int:
    """Executes the review run."""
    print(f"[*] Starting review for: {zip_path}", file=sys.stderr)
    print(f"[*] Orchestrator type : {orchestrator_type}", file=sys.stderr)
    print(f"[*] Mode              : {'Real LLM' if real_llm else 'Fake/Dry-Run (Default)'}", file=sys.stderr)
    print(f"[*] Security Debate   : {'Enabled' if with_debate else 'Disabled'}", file=sys.stderr)

    # 1. Environment and credentials configuration
    if real_llm:
        os.environ["USE_FAKE_LLM"] = "false"
        # Validate that credentials are set
        has_creds = (
            os.getenv("GEMINI_API_KEY") or
            os.getenv("GOOGLE_CLOUD_PROJECT")
        )
        if not has_creds:
            print(
                "[!] Error: Real LLM mode requested, but neither GOOGLE_CLOUD_PROJECT "
                "nor GEMINI_API_KEY was detected.",
                file=sys.stderr
            )
            return 1
    else:
        os.environ["USE_FAKE_LLM"] = "true"

    if with_debate:
        os.environ["ENABLE_SECURITY_DEBATE"] = "true"
    else:
        os.environ["ENABLE_SECURITY_DEBATE"] = "false"

    # 2. Verify zip file exists
    if not zip_path.exists():
        print(f"[!] Error: Zip file not found at {zip_path}", file=sys.stderr)
        return 1

    try:
        zip_bytes = zip_path.read_bytes()
    except Exception as e:
        print(f"[!] Error reading zip file: {e}", file=sys.stderr)
        return 1

    # 3. Setup workspace and extract
    with tempfile.TemporaryDirectory() as temp_dir_path:
        try:
            manifest = HardenedZipExtractor.extract(zip_bytes, temp_dir_path)
            corpus_summary = {
                "file_count": manifest.total_extracted_count,
                "total_bytes": manifest.total_extracted_bytes,
                "skipped_files": len(manifest.skipped_files),
                "skipped_log": {
                    k: {"skipped_reason": v.skipped_reason}
                    for k, v in manifest.skipped_files.items()
                }
            }
        except IngestionError as e:
            print(f"[!] Ingestion failed: {e}", file=sys.stderr)
            return 1

        # 4. Instantiate orchestrator
        if orchestrator_type == "in_process":
            orch = InProcessOrchestrator()
        else:
            orch = AdkOrchestrator()

        orch.start_run()
        redaction_ctx = orch.get_redaction_context()

        # Build corpus and run pre-flight secret scan
        corpus = build_corpus(temp_dir_path, manifest)
        gate_findings = run_secret_scan(corpus, redaction_ctx)

        # Update orchestrator shared state
        orch.set_corpus(corpus)
        orch.set_corpus_summary(corpus_summary)
        orch.run_secret_gate(gate_findings)

        # 5. Run Specialists
        print("[*] Running Correctness Specialist...", file=sys.stderr)
        orch.run_specialist("correctness", make_correctness_specialist(orch))

        print("[*] Running Security Specialist (with AST baseline)...", file=sys.stderr)
        await orch.run_specialist_async("security", make_security_specialist(orch))

        print("[*] Running Blast Radius Specialist...", file=sys.stderr)
        orch.run_specialist("blast_radius", make_blast_radius_specialist(orch))

        # 6. Compile final report
        print("[*] Compiling review report...", file=sys.stderr)
        try:
            report = orch.compile_report()
        except Exception as e:
            print(f"[!] Compilation failed: {e}", file=sys.stderr)
            return 1

    # 7. Print summary and output JSON
    print("\n" + "=" * 50, file=sys.stderr)
    print("REVIEW COMPLETE SUMMARY", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(f"Run ID             : {report.run_metadata['run_id']}", file=sys.stderr)
    print(f"Compilation Mode   : {report.run_metadata['compilation_mode']}", file=sys.stderr)
    print(f"Active Findings    : {len(report.findings)}", file=sys.stderr)
    print(f"Secret Scan Gate   : {len(report.secret_scan_summary)} findings found", file=sys.stderr)
    print(f"Validation Warnings: {len(report.validator_warnings)} warnings", file=sys.stderr)
    for w in report.validator_warnings:
        print(f"  - WARNING: {w}", file=sys.stderr)
    print("=" * 50 + "\n", file=sys.stderr)

    # Format JSON output
    report_json = report.model_dump_json(indent=2)
    
    if output_path:
        try:
            Path(output_path).write_text(report_json, encoding="utf-8")
            print(f"[+] Saved report JSON to {output_path}", file=sys.stderr)
        except Exception as e:
            print(f"[!] Failed to write output JSON to {output_path}: {e}", file=sys.stderr)
            return 1
    else:
        # Print JSON report to stdout
        print(report_json)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run automated multi-agent code review on a sample repository zip."
    )
    parser.add_argument(
        "--zip",
        type=str,
        default="samples/driftstore.zip",
        help="Path to the repository zip file (default: samples/driftstore.zip)."
    )
    parser.add_argument(
        "--orchestrator",
        choices=["adk", "in_process"],
        default="adk",
        help="Type of orchestrator to use (default: adk)."
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="Run using real Gemini/Vertex API (requires API key credentials, default: fake mode)."
    )
    parser.add_argument(
        "--with-debate",
        action="store_true",
        help="Enable the security debate loop (gated behind this flag)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional file path to save the final report JSON."
    )

    args = parser.parse_args()
    zip_path = Path(args.zip)

    try:
        return asyncio.run(
            run_review(
                zip_path=zip_path,
                orchestrator_type=args.orchestrator,
                real_llm=args.real,
                with_debate=args.with_debate,
                output_path=args.output
            )
        )
    except KeyboardInterrupt:
        print("\n[!] Execution interrupted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
