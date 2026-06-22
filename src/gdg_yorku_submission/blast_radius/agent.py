import os
import ast
import time
import logging
from typing import List, Tuple, Any, Callable, Dict, Set
from gdg_yorku_submission.schemas import ReviewFinding, Location
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.blast_radius.orbit_client import OrbitClient

logger = logging.getLogger(__name__)

class PythonSymbolExtractor(ast.NodeVisitor):
    def __init__(self) -> None:
        # Maps symbol to set of line numbers in the file
        self.symbols: Dict[str, Set[int]] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.name
            self.symbols.setdefault(name, set()).add(node.lineno)
            if alias.asname:
                self.symbols.setdefault(alias.asname, set()).add(node.lineno)
            # Support top-level sub-package imports
            if "." in name:
                parts = name.split(".")
                self.symbols.setdefault(parts[0], set()).add(node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        # Also index the module itself if present
        if module:
            self.symbols.setdefault(module, set()).add(node.lineno)
            if "." in module:
                parts = module.split(".")
                self.symbols.setdefault(parts[0], set()).add(node.lineno)
                
        for alias in node.names:
            if alias.name != "*":
                full_name = f"{module}.{alias.name}" if module else alias.name
                self.symbols.setdefault(full_name, set()).add(node.lineno)
                self.symbols.setdefault(alias.name, set()).add(node.lineno)
                if alias.asname:
                    self.symbols.setdefault(alias.asname, set()).add(node.lineno)
                    full_asname = f"{module}.{alias.asname}" if module else alias.asname
                    self.symbols.setdefault(full_asname, set()).add(node.lineno)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.setdefault(node.name, set()).add(node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.symbols.setdefault(node.name, set()).add(node.lineno)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.symbols.setdefault(node.name, set()).add(node.lineno)
        self.generic_visit(node)


def run_blast_radius_review(orch: Any) -> Tuple[List[ReviewFinding], str, str]:
    """
    Runs the blast radius review perspective using the Orbit API Client.
    Queries the prefetched GitLab Knowledge Graph and returns structured impact findings.
    Fails safe if Orbit is unconfigured or unreachable.
    """
    client = OrbitClient()

    # 1. Configuration Check
    if not client.is_configured():
        return [], "disabled", "Orbit / GitLab Knowledge Graph adapter unconfigured"

    # 2. Health check connection check
    if not client.health_check():
        return [], "unavailable", "Orbit / GitLab Knowledge Graph API is unavailable"

    corpus = orch.get_corpus()
    findings: List[ReviewFinding] = []

    # 3. Extract Python files from prompt_exposed corpus
    python_files = [
        cf for cf in corpus.values()
        if cf.exposure_status == "prompt_exposed" and cf.normalized_path.endswith(".py")
    ]

    # Map of unique symbol name -> list of tuples (cf_file_object, redacted_line_number)
    symbol_occurrences: Dict[str, List[Tuple[Any, int]]] = {}

    # Extract symbols and map to coordinates
    for cf in python_files:
        try:
            tree = ast.parse(cf.redacted_text)
            extractor = PythonSymbolExtractor()
            extractor.visit(tree)
        except Exception as e:
            logger.warning(f"Failed to parse AST for {cf.normalized_path}: {e}")
            continue

        # Keep only the most-qualified symbol (longest name string length) per line (Item 8)
        # NOTE: This is a conscious design choice that avoids duplicate findings per import line.
        # It silently lowers recall (e.g. 'Counter' is not queried next to 'defaultdict' on the same line),
        # which is accepted to keep report findings consolidated.
        line_symbols: Dict[int, List[str]] = {}
        for symbol, lines in extractor.symbols.items():
            for l in lines:
                line_symbols.setdefault(l, []).append(symbol)

        for l, symbols_on_line in line_symbols.items():
            if not symbols_on_line:
                continue
            most_qualified = max(symbols_on_line, key=len)
            symbol_occurrences.setdefault(most_qualified, []).append((cf, l))

    # Bounded querying (Item 3)
    unique_symbols = sorted(list(symbol_occurrences.keys()))
    unique_symbols = unique_symbols[:20]  # Cap at 20 unique symbols

    start_time = time.time()
    max_query_time = 2.0  # Max 2.0 seconds total elapsed wall-clock budget
    query_cache: Dict[str, Any] = {}

    for symbol in unique_symbols:
        elapsed = time.time() - start_time
        if elapsed > max_query_time:
            logger.warning(f"Orbit query wall-clock budget exceeded ({elapsed:.2f}s > {max_query_time}s); stopping queries.")
            break

        try:
            impact = client.query_symbol(symbol)
            query_cache[symbol] = impact
        except Exception as e:
            logger.error(f"Error querying Orbit for symbol '{symbol}': {e}")
            query_cache[symbol] = None

    # Generate findings from cached query results
    for symbol, impact in query_cache.items():
        if not impact:
            continue

        has_impact = (
            bool(impact.affected_projects) or
            bool(impact.dependencies) or
            bool(impact.pipelines) or
            bool(impact.merge_requests) or
            bool(impact.related_vulnerabilities)
        )
        if not has_impact:
            continue

        # Construct descriptive claim containing dependencies if present (Item 7)
        claim_parts = [f"Blast Radius for symbol '{symbol}':"]
        if impact.affected_projects:
            claim_parts.append(f"affects {len(impact.affected_projects)} projects {impact.affected_projects};")
        if impact.dependencies:
            claim_parts.append(f"depends on {impact.dependencies};")
        if impact.pipelines:
            failing = sum(1 for p in impact.pipelines if p.status == "failed")
            claim_parts.append(f"{len(impact.pipelines)} pipelines ({failing} failed);")
        if impact.merge_requests:
            claim_parts.append(f"{len(impact.merge_requests)} merge requests;")
        if impact.related_vulnerabilities:
            claim_parts.append(f"{len(impact.related_vulnerabilities)} vulnerabilities;")

        claim = " ".join(claim_parts).rstrip(";")

        # Determine severity, capped below the SEVERITY_FLOOR (max MEDIUM) (Item 2)
        severity = Severity.INFO
        if impact.related_vulnerabilities:
            max_vuln_sev = Severity.INFO
            for v in impact.related_vulnerabilities:
                v_sev_str = v.severity.lower()
                if v_sev_str == "critical":
                    v_sev = Severity.CRITICAL
                elif v_sev_str == "high":
                    v_sev = Severity.HIGH
                elif v_sev_str in ("medium", "major"):
                    v_sev = Severity.MEDIUM
                elif v_sev_str in ("low", "minor"):
                    v_sev = Severity.LOW
                else:
                    v_sev = Severity.INFO
                if v_sev > max_vuln_sev:
                    max_vuln_sev = v_sev
            severity = max_vuln_sev

        if not impact.related_vulnerabilities and any(p.status == "failed" for p in impact.pipelines):
            severity = Severity.MEDIUM

        # Cap severity below floor (Item 2)
        if severity > Severity.MEDIUM:
            severity = Severity.MEDIUM

        # Generate findings for each file and mapped line coordinate (Item 4)
        for cf, redacted_line in symbol_occurrences[symbol]:
            original_line = cf.map_line(redacted_line)

            # Existence/bounds checks (Item 4)
            if original_line < 1 or original_line > cf.original_line_count:
                logger.warning(
                    f"Orbit symbol '{symbol}' line {original_line} out of bounds for '{cf.normalized_path}' "
                    f"(original line count: {cf.original_line_count}). Skipping."
                )
                continue

            # Location of the symbol definition/import
            location = Location(
                path=cf.normalized_path,
                line_start=original_line,
                line_end=original_line
            )

            # Deterministic stable provisional ID
            import hashlib
            anchor_str = f"blast_radius_agent:blast_radius:{cf.normalized_path}:{original_line}:blast_radius:{symbol}"
            prov_id = f"prov-blast-{hashlib.sha256(anchor_str.encode('utf-8')).hexdigest()[:12]}"

            # Metadata for the finding containing the raw structured data
            metadata = {
                "symbol": symbol,
                "rule_or_category": "blast_radius",
                "affected_projects": impact.affected_projects,
                "dependencies": impact.dependencies,
                "pipelines": [p.model_dump() for p in impact.pipelines],
                "merge_requests": [mr.model_dump() for mr in impact.merge_requests],
                "related_vulnerabilities": [v.model_dump() for v in impact.related_vulnerabilities]
            }

            finding = ReviewFinding(
                id=prov_id,
                source_agent="blast_radius_agent",
                perspective="blast_radius",
                severity=severity,
                location=location,
                claim=claim,
                evidence_ref=[f"file:{cf.normalized_path}#{original_line}-{original_line}"],
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
