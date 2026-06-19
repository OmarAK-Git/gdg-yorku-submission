import hashlib
import re
from typing import Dict, List, Set, Tuple
from gdg_yorku_submission.schemas import Location, GateFinding, CorpusFile, ReviewFinding
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.preflight.redaction import RedactionContext, GLOBAL_REDACTION_CONTEXT

# Regex patterns for different secret types
PEM_PATTERN = re.compile(
    r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----.*?-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----",
    re.DOTALL
)

PATTERNS = {
    "AWS Access Key ID": re.compile(r"\b((?:AKIA|ASCA|AGPA|AIDA)[A-Z0-9]{16})\b"),
    "AWS Secret Access Key": re.compile(
        r"(?i)\b(aws_secret_access_key|aws_secret|secret_key|secret_access_key)[ \t]*[:=][ \t]*['\"]?([A-Za-z0-9/+=]{40})['\"]?"
    ),
    "Google API Key": re.compile(r"\b(AIza[0-9A-Za-z-_]{35})\b"),
    "Slack Token": re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b"),
    "GitHub PAT": re.compile(r"\b(ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z]{82})\b"),
    "Stripe API Key": re.compile(r"\b(sk_live_[0-9a-zA-Z]{24})\b"),
    "Database Connection String": re.compile(
        r"(?i)\b[a-z0-9+.-]+://[^:\s#]+:[^@\s#]+@[^\s#]+\b"
    ),
    "Generic Secret Assignment": re.compile(
        r"(?i)\b(api[_-]?key|secret|password|passwd|token|auth|credential|db[_-]?pass(?:word)?)[ \t]*[:=][ \t]*['\"]([^'\"]{8,})['\"]"
    ),
    "Dotenv Assignment": re.compile(
        r"(?i)^[A-Z0-9_]*(?:SECRET|KEY|PASSWORD|TOKEN|PASS|PWD|CREDENTIAL)[A-Z0-9_]*[ \t]*=[ \t]*['\"]?([^'\"\r\n]{8,})['\"]?"
    )
}

CRITICAL_SECRET_TYPES = {
    "PEM Private Key",
    "AWS Secret Access Key",
    "Database Password",
    "Password",
    "Database Connection String"
}

def scan_file_for_secrets(
    path: str,
    text: str,
    exposure_status: str,
    context: RedactionContext
) -> List[GateFinding]:
    """
    Scans a single file's text for secrets using deterministic patterns.
    Registers found secrets in the provided RedactionContext.
    """
    findings: List[GateFinding] = []
    
    # Track coordinates to avoid duplicate findings for the same match
    seen_matches: Set[Tuple[int, int, str]] = set()
    # Track occurrence counts for deterministic, salt-independent finding IDs
    occurrence_counts: Dict[Tuple[str, int, str], int] = {}

    # 1. Process multi-line PEM private keys via full text scanning (BUG-001)
    for m in PEM_PATTERN.finditer(text):
        pem_value = m.group(0)
        
        # Register secret
        context.register_secret(pem_value, "PEM Private Key")
        fp = context.get_fingerprint(pem_value)
        
        start_char = m.start()
        end_char = m.end()
        line_start = text[:start_char].count('\n') + 1
        line_end = line_start + text[start_char:end_char].count('\n')
        
        # Severity mapping: prompt_exposed -> CRITICAL (private key is critical credential); others -> INFO
        severity = Severity.CRITICAL if exposure_status == "prompt_exposed" else Severity.INFO
        
        loc = Location(path=path, line_start=line_start, line_end=line_end)
        
        # Stable finding ID (BUG-011)
        key = (path, line_start, "PEM Private Key")
        occurrence_counts[key] = occurrence_counts.get(key, 0) + 1
        ordinal = occurrence_counts[key]
        finding_id = hashlib.sha256(
            f"preflight_secret_gate:{path}:{line_start}:PEM Private Key:{ordinal}".encode("utf-8")
        ).hexdigest()
        
        findings.append(
            GateFinding(
                id=finding_id,
                source_agent="preflight_secret_gate",
                perspective="security",
                severity=severity,
                location=loc,
                claim=f"Exposed PEM Private Key in {path}",
                evidence_ref=[f"file:{path}#{line_start}-{line_end}"],
                secret_type="PEM Private Key",
                fingerprint=fp,
                exposure_status=exposure_status
            )
        )
        seen_matches.add((line_start, line_end, pem_value))

    # 2. Process other line-based secrets
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        line_num = idx + 1
        
        # Skip if this line is part of a PEM block we already processed
        is_in_pem = False
        for start, end, _ in seen_matches:
            if start <= line_num <= end:
                is_in_pem = True
                break
        if is_in_pem:
            continue
            
        for secret_type, regex in PATTERNS.items():
            for m in regex.finditer(line):
                # If there are capture groups, extract the last capture group.
                if regex.groups > 0:
                    val = m.group(regex.groups)
                    # Strip outer quotes if captured
                    val = val.strip("'\"")
                else:
                    val = m.group(0)
                    
                if not val or len(val.strip()) < 8:
                    continue
                
                # Check for duplicate
                coord = (line_num, line_num, val)
                if coord in seen_matches:
                    continue
                seen_matches.add(coord)
                
                # Refine secret type dynamically from matched key names (BUG-010)
                refined_type = secret_type
                if secret_type == "Generic Secret Assignment":
                    var_name = m.group(1).lower()
                    if any(x in var_name for x in ["db_password", "database_password", "dbpass", "db_pass"]):
                        refined_type = "Database Password"
                    elif any(x in var_name for x in ["password", "passwd", "pwd"]):
                        refined_type = "Password"
                    elif "key" in var_name:
                        refined_type = "API Key"
                    else:
                        refined_type = "Secret"
                elif secret_type == "Dotenv Assignment":
                    key_part = line.split("=")[0].strip().lower()
                    if any(x in key_part for x in ["db_password", "database_password", "dbpass", "db_pass"]):
                        refined_type = "Database Password"
                    elif any(x in key_part for x in ["password", "passwd", "pwd"]):
                        refined_type = "Password"
                    elif "key" in key_part:
                        refined_type = "API Key"
                    else:
                        refined_type = "Secret"
                
                # Register secret
                context.register_secret(val, refined_type)
                fp = context.get_fingerprint(val)
                
                # Severity Mapping:
                # - prompt_exposed = high (unless it is a critical credential -> critical)
                # - ignored / excluded = info (advisory)
                if exposure_status == "prompt_exposed":
                    severity = Severity.CRITICAL if refined_type in CRITICAL_SECRET_TYPES else Severity.HIGH
                else:
                    severity = Severity.INFO
                    
                loc = Location(path=path, line_start=line_num, line_end=line_num)
                
                # Stable finding ID (BUG-011)
                key = (path, line_num, refined_type)
                occurrence_counts[key] = occurrence_counts.get(key, 0) + 1
                ordinal = occurrence_counts[key]
                finding_id = hashlib.sha256(
                    f"preflight_secret_gate:{path}:{line_num}:{refined_type}:{ordinal}".encode("utf-8")
                ).hexdigest()
                
                findings.append(
                    GateFinding(
                        id=finding_id,
                        source_agent="preflight_secret_gate",
                        perspective="security",
                        severity=severity,
                        location=loc,
                        claim=f"Exposed {refined_type} in {path}",
                        evidence_ref=[f"file:{path}#{line_num}"],
                        secret_type=refined_type,
                        fingerprint=fp,
                        exposure_status=exposure_status
                    )
                )
                
    return findings


def run_secret_scan(
    corpus: Dict[str, CorpusFile],
    context: RedactionContext = None
) -> List[GateFinding]:
    """
    Scans the entire corpus for secrets, populates the RedactionContext,
    and updates redacted_text of all CorpusFile models.
    """
    if context is None:
        context = GLOBAL_REDACTION_CONTEXT
        
    all_findings: List[GateFinding] = []
    
    # 1. Scan files that have valid source text
    for path, corpus_file in corpus.items():
        if corpus_file.ingest_status == "success" and corpus_file.original_text:
            findings = scan_file_for_secrets(
                path=corpus_file.normalized_path,
                text=corpus_file.original_text,
                exposure_status=corpus_file.exposure_status,
                context=context
            )
            all_findings.extend(findings)
            
    # 2. Redact text for all corpus files using registered secrets
    for path, corpus_file in corpus.items():
        if corpus_file.original_text:
            corpus_file.redacted_text = context.redact(corpus_file.original_text)
            
    return all_findings


def promote_gate_findings(gate_findings: List[GateFinding]) -> List[ReviewFinding]:
    """
    Converts prompt_exposed high/critical GateFindings into ReviewFindings.
    """
    promoted: List[ReviewFinding] = []
    for gf in gate_findings:
        if gf.exposure_status == "prompt_exposed" and gf.severity in (Severity.HIGH, Severity.CRITICAL):
            # Promote to ReviewFinding (which is alias to Finding)
            rf = ReviewFinding(
                id=f"promoted-{gf.id}",
                source_agent="preflight_secret_gate",
                perspective="security",
                severity=gf.severity,
                location=gf.location,
                claim=gf.claim,
                evidence_ref=gf.evidence_ref,
                status="active",
                metadata={
                    "secret_type": gf.secret_type,
                    "fingerprint": gf.fingerprint,
                    "exposure_status": gf.exposure_status,
                    "rule_or_category": "exposed_secret",
                }
            )
            promoted.append(rf)
    return promoted
