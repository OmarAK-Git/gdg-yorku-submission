"""
Out-of-band validator-rejection demo hook CLI tool.
This module is isolated from production code paths and HTTP endpoints.
It is strictly for demonstrating report validator failure on corrupted data
and verifying the redaction invariant on the serialized report.
"""

import argparse
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple

from gdg_yorku_submission.ingestion import HardenedZipExtractor
from gdg_yorku_submission.corpus import build_corpus
from gdg_yorku_submission.preflight.secrets import run_secret_scan
from gdg_yorku_submission.security.deterministic import make_security_specialist
from gdg_yorku_submission.orchestrator import InProcessOrchestrator
from gdg_yorku_submission.coordinator.validator import validate_report_invariants
from gdg_yorku_submission.schemas import OmitLedgerEntry, Severity, Location

class DemoResult:
    """Structured result containing validation errors before and after corruption."""
    def __init__(
        self,
        baseline_errors: List[str],
        corrupted_errors: List[str],
        redacted_errors: List[str] = None,
        target_finding_id: str = None,
        secret_value: str = None,
        secret_placeholder: str = None,
        secret_fingerprint: str = None,
        source_file_original: str = None,
        source_file_redacted: str = None,
        serialized_report: str = None
    ) -> None:
        self.baseline_errors = baseline_errors
        self.corrupted_errors = corrupted_errors
        self.redacted_errors = redacted_errors or []
        self.target_finding_id = target_finding_id
        self.secret_value = secret_value
        self.secret_placeholder = secret_placeholder
        self.secret_fingerprint = secret_fingerprint
        self.source_file_original = source_file_original or ""
        self.source_file_redacted = source_file_redacted or ""
        self.serialized_report = serialized_report or ""

def run_demo_logic(action: str, zip_path: Path) -> DemoResult:
    """
    Runs the out-of-band validation demo pipeline.
    Ingests the target zip, runs the baseline security scanners,
    generates a valid terminal report, validates it (negative control),
    applies the requested corruption, validates the corrupted report,
    and returns a structured DemoResult.
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found at '{zip_path}'")

    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = HardenedZipExtractor.extract(zip_bytes, tmpdir)
        corpus = build_corpus(tmpdir, manifest)

        orch = InProcessOrchestrator()
        orch.start_run()

        ctx = orch.get_redaction_context()
        gate_findings = run_secret_scan(corpus, ctx)
        orch.set_corpus(corpus)
        orch.set_corpus_summary({"file_count": len(corpus), "total_bytes": len(zip_bytes)})
        orch.run_secret_gate(gate_findings)

        # Run deterministic security baseline pass
        orch.run_specialist("security", make_security_specialist(orch))

        # Finalize IDs
        orch.finalize_ids()

        state = orch.read_state()
        input_findings = state["findings"]

        if not input_findings:
            raise ValueError("No input findings generated. Verify the zip has Python/secret files.")

        # Compile a valid terminal report (Clean production output, no metadata injection)
        report = orch.compile_terminal_report()

        # 1. Negative Control Check: Validate baseline report before mutating
        baseline_errors = validate_report_invariants(report, input_findings, corpus)

        corrupted_errors: List[str] = []
        redacted_errors: List[str] = []
        target_finding_id = None
        secret_value = None
        secret_placeholder = None
        secret_fingerprint = None
        source_file_original = ""
        source_file_redacted = ""
        serialized_report = ""

        # 2. Process based on action
        if action == "drop-high":
            # Find the first high/critical severity finding to drop
            target_finding = None
            for rf in report.findings:
                if rf.severity in (Severity.HIGH, Severity.CRITICAL):
                    target_finding = rf
                    break

            if not target_finding:
                raise ValueError("No HIGH or CRITICAL finding found to drop.")

            target_finding_id = target_finding.id
            
            # Remove it from findings lists and severity counts
            report.findings = [rf for rf in report.findings if rf.id != target_finding.id]
            report.high_critical_findings = [rf for rf in report.high_critical_findings if rf.id != target_finding.id]
            if target_finding.severity.value in report.severity_counts:
                report.severity_counts[target_finding.severity.value] = max(
                    0, report.severity_counts[target_finding.severity.value] - 1
                )

            # Update ledger: remove from included, add to omitted
            report.accounting_ledger.included = [fid for fid in report.accounting_ledger.included if fid != target_finding.id]
            report.accounting_ledger.omitted.append(
                OmitLedgerEntry(
                    id=target_finding.id,
                    reason="Deliberate corruption for demo out-of-band test"
                )
            )

        elif action == "corrupt-location":
            if not report.findings:
                raise ValueError("No findings available in report to corrupt.")

            target_finding = report.findings[0]
            target_finding_id = target_finding.id

            # Corrupt location coordinates
            target_finding.location = Location(
                path=target_finding.location.path,
                line_start=9999,
                line_end=10000
            )

        elif action == "corrupt-evidence-ref":
            if not report.findings:
                raise ValueError("No findings available in report to corrupt.")

            target_finding = report.findings[0]
            target_finding_id = target_finding.id

            # Corrupt evidence reference coordinate
            target_finding.evidence_ref = [f"file:{target_finding.location.path}#9999-10000"]

        elif action == "leak-secret":
            # Real pipeline check - NO manual raw secret injection or manual redaction context call.
            # Locate the registered raw secret and its placeholder.
            registered_secrets = list(ctx.secrets_to_placeholders.keys())
            if not registered_secrets:
                raise ValueError("No secrets registered in context from the zip file.")

            secret_value = registered_secrets[0]
            secret_placeholder = ctx.secrets_to_placeholders[secret_value]
            secret_fingerprint = ctx.secrets_to_fingerprints[secret_value]

            # Find the unredacted/redacted text for the file containing the secret
            for corpus_file in corpus.values():
                if secret_value in corpus_file.original_text:
                    source_file_original = corpus_file.original_text
                    source_file_redacted = corpus_file.redacted_text
                    break

            # Serialize the unmodified compiled report surface
            serialized_report = report.model_dump_json()

        else:
            raise ValueError(f"Unknown action '{action}'")

        # 3. Run report validator invariants on mutated report (except for leak-secret which remains uncorrupted)
        if action != "leak-secret":
            raw_errors = validate_report_invariants(report, input_findings, corpus)
            corrupted_errors = raw_errors
            # Keep redacted_errors backward compatible for other corruption checks
            redacted_errors = [ctx.redact(err) for err in raw_errors]

        return DemoResult(
            baseline_errors=baseline_errors,
            corrupted_errors=corrupted_errors,
            redacted_errors=redacted_errors,
            target_finding_id=target_finding_id,
            secret_value=secret_value,
            secret_placeholder=secret_placeholder,
            secret_fingerprint=secret_fingerprint,
            source_file_original=source_file_original,
            source_file_redacted=source_file_redacted,
            serialized_report=serialized_report
        )

def run_demo(action: str, zip_path: Path) -> int:
    """Wrapper function to parse the logic result and print it to stdout for CLI use."""
    try:
        result = run_demo_logic(action, zip_path)
    except Exception as e:
        print(f"Error executing pipeline: {e}", file=sys.stderr)
        return 1

    if result.baseline_errors:
        print("=== BASELINE VALIDATION FAILED (REGRESSION DETECTED) ===")
        for err in result.baseline_errors:
            print(f"Baseline Error: {err}")
        return 2

    if action == "leak-secret":
        # Check secret redaction invariants on the serialized report
        secret_value = result.secret_value
        secret_fingerprint = result.secret_fingerprint
        report_json = result.serialized_report

        if not secret_value or not secret_fingerprint:
            print("Error: No secrets registered in context.", file=sys.stderr)
            return 1

        # Check for leak
        if secret_value in report_json:
            print("\n=== LEAK-DETECTED: REDACTION INVARIANT VIOLATED ===")
            print(f"Raw secret '{secret_value}' was found in the serialized report output!")
            print("===================================================\n")
            return 1
        
        # Check fingerprint presence
        if secret_fingerprint not in report_json:
            print("\n=== LEAK-DETECTED: REDACTION INVARIANT VIOLATED ===")
            print(f"Redaction fingerprint '{secret_fingerprint}' was missing from the report output!")
            print("===================================================\n")
            return 1

        print("\n=== PASS: REDACTION INVARIANT VALIDATED ===")
        if result.source_file_original:
            print("Raw secret was found in the source file original text.")
        if result.source_file_redacted:
            print("Raw secret was NOT found in the source file redacted text.")
        print("Raw secret was NOT found in the final compiled report JSON.")
        print(f"Salted fingerprint '{secret_fingerprint}' is present in the report JSON.")
        print("============================================\n")
        return 0

    else:
        # Existing exit code logic for corruption actions
        if result.corrupted_errors:
            print("\n=== VALIDATOR REJECTED REPORT ===")
            for err in result.redacted_errors:
                print(f"Validator Invariant Violation: {err}")
            print("=================================\n")
            return 1
        else:
            print("\n=== VALIDATOR ACCEPTED REPORT ===\n")
            return 0

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Out-of-band validator-rejection demo hook CLI tool."
    )
    parser.add_argument(
        "action",
        choices=["drop-high", "corrupt-location", "corrupt-evidence-ref", "leak-secret"],
        help="The corruption action to perform and validate."
    )
    parser.add_argument(
        "zip_path",
        type=Path,
        help="Path to the repository zip archive."
    )
    args = parser.parse_args()

    sys.exit(run_demo(args.action, args.zip_path))

if __name__ == "__main__":
    main()
