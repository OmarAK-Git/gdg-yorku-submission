import hashlib
import time
import logging
from typing import List, Tuple, Any, Callable
from gdg_yorku_submission.schemas import ReviewFinding, Location
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.blast_radius.orbit_client import OrbitClient
from gdg_yorku_submission.blast_radius.orbit_graph import OrbitQueryResult
from gdg_yorku_submission.blast_radius.impact import build_impact_graph, summarize_blast

logger = logging.getLogger(__name__)


def redact_val(v: Any, redaction_ctx: Any) -> Any:
    """Recursively redacts Orbit-derived strings to maintain prompt/data safety."""
    if not redaction_ctx:
        return v
    if isinstance(v, str):
        return redaction_ctx.redact(v)
    elif isinstance(v, list):
        return [redact_val(item, redaction_ctx) for item in v]
    elif isinstance(v, dict):
        return {k: redact_val(val, redaction_ctx) for k, val in v.items()}
    return v


def run_blast_radius_review(orch: Any) -> Tuple[List[ReviewFinding], str, str]:
    """
    Runs the blast radius review perspective using the Orbit API Client.
    Queries the prefetched GitLab Knowledge Graph and returns structured impact findings.
    Fails safe if Orbit is unconfigured or unreachable.
    """
    client = OrbitClient()

    # 1. Configuration Check
    if not client.is_configured():
        return [], "disabled", "Orbit client is unconfigured (missing API URL, token, or project path)."

    # 2. Connectivity check
    if not client.health_check():
        return [], "unavailable", "Orbit / GitLab Knowledge Graph API is unavailable."

    # 3. Fetch Definitions + Calls + Imports + Vulnerabilities + Pipelines + Merge Requests
    try:
        definitions = client.fetch_definitions()
    except Exception as e:
        logger.error(f"Failed to fetch definitions: {e}")
        return [], "unavailable", f"Failed to fetch definitions: {e}"

    try:
        calls = client.fetch_calls()
    except Exception as e:
        logger.error(f"Failed to fetch calls: {e}")
        return [], "unavailable", f"Failed to fetch calls: {e}"

    # For auxiliary queries, degrade to empty rather than failing the run
    imports = OrbitQueryResult()
    try:
        imports = client.fetch_imports()
    except Exception as e:
        logger.warning(f"Failed to fetch imports (degraded to empty): {e}")

    vulns = OrbitQueryResult()
    try:
        vulns = client.fetch_vulnerabilities()
    except Exception as e:
        logger.warning(f"Failed to fetch vulnerabilities (degraded to empty): {e}")

    pipelines = OrbitQueryResult()
    try:
        pipelines = client.fetch_pipelines()
    except Exception as e:
        logger.warning(f"Failed to fetch pipelines (degraded to empty): {e}")

    mrs = OrbitQueryResult()
    try:
        mrs = client.fetch_merge_requests()
    except Exception as e:
        logger.warning(f"Failed to fetch merge requests (degraded to empty): {e}")

    # Build the impact graph
    impact_graph = build_impact_graph(definitions, calls)
    
    # Get blast summaries ordered by blast size descending
    summaries = summarize_blast(impact_graph)

    corpus = orch.get_corpus()
    findings: List[ReviewFinding] = []

    # Get counts for project-level elements
    num_vulns = len(vulns.nodes_of_type("Vulnerability"))
    num_pipelines = len(pipelines.nodes_of_type("Pipeline"))
    num_mrs = len(mrs.nodes_of_type("MergeRequest"))

    # Get run-specific RedactionContext to sanitize external data from Orbit
    redaction_ctx = orch.get_redaction_context() if hasattr(orch, "get_redaction_context") else None

    start_time = time.time()
    max_processing_time = 2.0  # 2 seconds total budget
    max_findings = 20

    for summary in summaries:
        # Check processing wall-clock budget
        if time.time() - start_time > max_processing_time:
            logger.warning("Blast radius review processing wall-clock budget exceeded; stopping.")
            break

        if len(findings) >= max_findings:
            break

        # 4. Resolve file path in corpus (case-insensitive, normalized forward-slash)
        def_file_path = summary.definition.file_path
        if not def_file_path:
            continue
        
        normalized_path = def_file_path.replace("\\", "/").lower()
        corpus_key = None
        for k in corpus.keys():
            if k.lower() == normalized_path:
                corpus_key = k
                break

        if corpus_key is None:
            # File wasn't uploaded / missing from corpus -> skip
            continue

        corpus_file = corpus[corpus_key]
        start_line = summary.definition.start_line
        end_line = summary.definition.end_line

        # Bounds check
        if not (1 <= start_line <= end_line <= corpus_file.original_line_count):
            logger.warning(
                f"Coordinates out of bounds for {corpus_file.normalized_path}: "
                f"[{start_line}, {end_line}] (original lines: {corpus_file.original_line_count}). Skipping."
            )
            continue

        # Find imports of the file for enrichment
        file_imports = [
            node.get("import_path")
            for node in imports.nodes_of_type("ImportedSymbol")
            if node.get("file_path") and node.get("file_path").replace("\\", "/").lower() == normalized_path
        ]
        unique_imports = sorted(list(set(filter(None, file_imports))))

        # Build claim with redacted Orbit fields
        fqn_redacted = redact_val(summary.definition.fqn, redaction_ctx)
        claim_parts = [
            f"Changing `{fqn_redacted}` impacts {len(summary.dependent_ids)} definitions "
            f"across {len(summary.dependent_files)} files (call-graph blast radius)."
        ]
        if unique_imports:
            imports_redacted = redact_val(unique_imports[:5], redaction_ctx)
            imports_list = ", ".join(imports_redacted)
            claim_parts.append(f"File imports: {imports_list}.")
        if num_vulns > 0 or num_pipelines > 0 or num_mrs > 0:
            proj_parts = []
            if num_vulns > 0:
                proj_parts.append(f"{num_vulns} vulnerabilities")
            if num_pipelines > 0:
                proj_parts.append(f"{num_pipelines} pipelines")
            if num_mrs > 0:
                proj_parts.append(f"{num_mrs} merge requests")
            claim_parts.append(f"Project has: {', '.join(proj_parts)}.")

        claim = redact_val(" ".join(claim_parts), redaction_ctx)

        # Scale severity based on dependent definitions:
        # - >= 10 dependents: HIGH
        # - >= 3 dependents: MEDIUM
        # - >= 1 dependents: LOW
        num_deps = len(summary.dependent_ids)
        if num_deps >= 10:
            severity = Severity.HIGH
        elif num_deps >= 3:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        # If project contains active vulnerabilities, upgrade to MEDIUM
        if num_vulns > 0 and severity < Severity.MEDIUM:
            severity = Severity.MEDIUM

        # If project has failed pipelines, upgrade to MEDIUM
        has_failed_pipelines = any(
            n.get("status") == "failed"
            for n in pipelines.nodes_of_type("Pipeline")
        )
        if has_failed_pipelines and severity < Severity.MEDIUM:
            severity = Severity.MEDIUM

        # ALWAYS clamp to MEDIUM max to respect severity floor constraint
        # (This is load-bearing; ensures findings do not flood the critical lists)
        if severity > Severity.MEDIUM:
            severity = Severity.MEDIUM

        # Location of the definition
        # UPSTREAM DESIGN ASSUMPTION: Orbit indexes the original (unredacted) source repository.
        # Therefore, coordinates returned by Orbit represent the original file coordinates,
        # so we do NOT apply `map_line` to these coordinates.
        location = Location(
            path=corpus_file.normalized_path,
            line_start=start_line,
            line_end=end_line
        )

        # Deterministic stable provisional ID
        anchor_str = f"blast_radius_agent:blast_radius:{corpus_file.normalized_path}:{start_line}:{end_line}:{summary.definition.fqn}"
        prov_id = f"prov-blast-{hashlib.sha256(anchor_str.encode('utf-8')).hexdigest()[:12]}"

        # Metadata format with redacted Orbit fields
        metadata = {
            "symbol": redact_val(summary.definition.fqn, redaction_ctx),
            "rule_or_category": "blast_radius",
            "dependent_fqns": redact_val(sorted([
                impact_graph.defs[d].fqn
                for d in summary.dependent_ids
                if d in impact_graph.defs and impact_graph.defs[d].fqn
            ])[:20], redaction_ctx),
            "dependent_files": redact_val(sorted(list(summary.dependent_files))[:20], redaction_ctx),
            "import_paths": redact_val(unique_imports[:20], redaction_ctx),
            "pipelines": redact_val([
                {"id": n.id, "status": n.get("status"), "web_url": n.get("web_url")}
                for n in pipelines.nodes_of_type("Pipeline")
            ], redaction_ctx),
            "merge_requests": redact_val([
                {"id": n.id, "title": n.get("title"), "state": n.get("state"), "web_url": n.get("web_url")}
                for n in mrs.nodes_of_type("MergeRequest")
            ], redaction_ctx),
            "related_vulnerabilities": redact_val([
                {"id": n.id, "severity": n.get("severity"), "description": n.get("description")}
                for n in vulns.nodes_of_type("Vulnerability")
            ], redaction_ctx)
        }

        finding = ReviewFinding(
            id=prov_id,
            source_agent="blast_radius_agent",
            perspective="blast_radius",
            severity=severity,
            location=location,
            claim=claim,
            evidence_ref=[f"file:{corpus_file.normalized_path}#{start_line}-{end_line}"],
            status="active",
            metadata=metadata
        )
        findings.append(finding)

    return findings, "complete", ""


def make_blast_radius_specialist(orch: Any) -> Callable[[], Tuple[List[ReviewFinding], str, str]]:
    """
    Returns the blast-radius specialist Callable.
    """
    return lambda: run_blast_radius_review(orch)
