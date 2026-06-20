import re
from pathlib import Path
import pytest

from gdg_yorku_submission.correctness import (
    METHODOLOGY_PATH,
    load_methodology,
    validate_correctness_finding,
)

def test_methodology_file_exists():
    """Asserts that methodology.md exists and is non-empty."""
    assert METHODOLOGY_PATH.exists(), f"Methodology file not found at {METHODOLOGY_PATH}"
    assert METHODOLOGY_PATH.stat().st_size > 0, "Methodology file is empty"

def test_valid_markdown_structure():
    """
    Checks that the methodology file is well-formed Markdown.
    Asserts a clean heading structure (starts with H1, subsequent are H2/H3),
    balanced code blocks, and valid list formats.
    """
    content = load_methodology()
    lines = content.splitlines()
    
    # 1. Heading structure checks
    headings = []
    in_code_block = False
    
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
            
        if not in_code_block and stripped.startswith("#"):
            # Ensure space after #
            match = re.match(r"^(#+)(?:\s+(.*))?$", stripped)
            assert match, f"Line {idx}: Heading format is invalid: '{line}'"
            level = len(match.group(1))
            title = match.group(2)
            assert title, f"Line {idx}: Heading title cannot be empty"
            headings.append((level, title))
            
    assert not in_code_block, "Markdown has an unbalanced code block fence"
    assert len(headings) > 0, "Markdown must contain at least one heading"
    assert headings[0][0] == 1, "First heading must be level 1 (H1)"
    
    # Check that levels don't skip (e.g. H1 -> H3)
    prev_level = 1
    for level, title in headings[1:]:
        assert level <= prev_level + 1, f"Heading level skipped from H{prev_level} to H{level}: '{title}'"
        prev_level = level

def test_legacy_topics_absent_across_entire_document():
    """
    Asserts that no legacy topics (security, secrets, credentials, passwords,
    dependencies, TDD, Antigravity, or PASS/FIX) are present in the methodology.md
    file outside of an explicitly marked exclusions/non-goals section.
    """
    content = load_methodology()
    
    # Split the document into sections to allow exclusions if defined
    sections = re.split(r"\n##\s+", content)
    
    legacy_patterns = [
        re.compile(r"\bsecur(ity|ities)\b", re.IGNORECASE),
        re.compile(r"\bdependenc(y|ies)\b", re.IGNORECASE),
        re.compile(r"\bsecret(s)?\b", re.IGNORECASE),
        re.compile(r"\bpassword(s)?\b", re.IGNORECASE),
        re.compile(r"\bcredential(s)?\b", re.IGNORECASE),
        re.compile(r"\btdd\b", re.IGNORECASE),
        re.compile(r"\bantigravity\b", re.IGNORECASE),
        re.compile(r"\bpass/fix\b", re.IGNORECASE),
    ]
    
    for idx, section in enumerate(sections):
        section_lines = section.splitlines()
        if not section_lines:
            continue
        header = section_lines[0].lower()
        
        # If it's a section explicitly designated as excluded/non-goals/out-of-scope, we skip it
        if any(word in header for word in ["exclusion", "exclude", "non-goal", "out of scope", "out-of-scope"]):
            continue
            
        # Check every line in this active criteria section
        for line_num, line in enumerate(section_lines, 1):
            for pattern in legacy_patterns:
                match = pattern.search(line)
                assert not match, (
                    f"Legacy topic match '{match.group(0)}' found in active criteria section "
                    f"'{section_lines[0]}' line {line_num}: '{line.strip()}'"
                )

def test_correctness_core_focus_present_as_headings():
    """
    Asserts that the core correctness areas are presented as actual headings (H3)
    in the Markdown file.
    """
    content = load_methodology()
    
    # We expect H3 subheadings under Evaluation Categories
    h3_headings = [line.strip() for line in content.splitlines() if line.strip().startswith("###")]
    h3_lower = [h.lower() for h in h3_headings]
    
    assert any("intent" in h for h in h3_lower), "Missing H3 heading for intent verification"
    assert any("divergence" in h for h in h3_lower), "Missing H3 heading for spec-code divergence"
    assert any("traceability" in h for h in h3_lower), "Missing H3 heading for traceability"
    assert any("logic" in h for h in h3_lower), "Missing H3 heading for logic-vs-spec consistency"

def test_schema_fields_present_in_requirements_block():
    """
    Asserts that all 9 schema fields are listed under the Finding Schema Requirements block.
    """
    content = load_methodology()
    
    # Find the Finding Schema Requirements section
    match = re.search(r"## Finding Schema Requirements(.*?)(?:\n##|\Z)", content, re.DOTALL)
    assert match, "Missing 'Finding Schema Requirements' section"
    
    schema_section = match.group(1)
    
    # Find all list items (lines starting with - or *)
    list_items = re.findall(r"^\s*[-*]\s+`([^`]+)`", schema_section, re.MULTILINE)
    
    required_fields = {
        "id", "source_agent", "perspective", "severity", "location", "claim", "evidence_ref", "status", "metadata"
    }
    
    assert required_fields.issubset(set(list_items)), (
        f"Missing schema fields in requirements block. Expected {required_fields}, got {list_items}"
    )

def test_no_spec_severity_cap_rules():
    """
    Asserts that the no-spec severity cap (status no_spec_found_conformance_skipped)
    is explicitly capped at 'medium' in the rubric text, and ensures that
    no conflicting higher cap is mentioned.
    """
    content = load_methodology().lower()
    
    # Assert no-spec scenario and medium cap co-occur in the same paragraph/sentence
    match = re.search(r"no_spec_found_conformance_skipped.*medium|no specification.*medium", content)
    assert match, "Rubric must explicitly tie the no-spec fallback status/scenario to 'medium' severity"
    
    # Assert that no section claims the cap is high or critical
    assert "capped at high" not in content, "Invalid rubric statement: severity cap cannot be high"
    assert "capped at critical" not in content, "Invalid rubric statement: severity cap cannot be critical"
    assert "maximum severity of high" not in content, "Invalid rubric statement: severity cap cannot be high"
    assert "maximum severity of critical" not in content, "Invalid rubric statement: severity cap cannot be critical"

# --- Executable Invariant Tests (Fixture-based negative and positive validation) ---

@pytest.fixture
def base_valid_finding():
    return {
        "id": "correctness-f1",
        "source_agent": "correctness_agent",
        "perspective": "correctness",
        "severity": "high",
        "location": {
            "path": "src/app.py",
            "line_start": 10,
            "line_end": 15,
        },
        "claim": "The spec states functions return integers but code returns float",
        "evidence_ref": ["file:SPEC.md#10-12"],
        "status": "active",
        "metadata": {},
    }

def test_validator_accepts_valid_finding(base_valid_finding):
    """Asserts that a fully conforming correctness finding passes validation."""
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert not errors, f"Expected no validation errors, got: {errors}"

def test_validator_enforces_required_fields():
    """Asserts that missing fields are caught by the validator."""
    invalid_finding = {"id": "f1"}
    errors = validate_correctness_finding(invalid_finding, has_spec=True)
    assert any("Schema validation failed" in err for err in errors)

def test_validator_enforces_source_agent_and_perspective(base_valid_finding):
    """Asserts that source_agent and perspective are restricted to correctness agent."""
    base_valid_finding["source_agent"] = "security_debate"
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert any("Invalid source_agent" in err for err in errors)
    
    base_valid_finding["source_agent"] = "correctness_agent"
    base_valid_finding["perspective"] = "security"
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert any("Invalid perspective" in err for err in errors)

def test_validator_enforces_no_spec_severity_cap(base_valid_finding):
    """Asserts that findings are capped at medium when has_spec is False."""
    # When spec is present, high severity is fine
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert not errors
    
    # When spec is absent, high/critical severity must be rejected
    base_valid_finding["severity"] = "high"
    errors = validate_correctness_finding(base_valid_finding, has_spec=False)
    assert any("capped at medium" in err for err in errors)
    
    base_valid_finding["severity"] = "critical"
    errors = validate_correctness_finding(base_valid_finding, has_spec=False)
    assert any("capped at medium" in err for err in errors)
    
    # Medium severity is accepted
    base_valid_finding["severity"] = "medium"
    errors = validate_correctness_finding(base_valid_finding, has_spec=False)
    assert not errors
    
    # Low severity is accepted
    base_valid_finding["severity"] = "low"
    errors = validate_correctness_finding(base_valid_finding, has_spec=False)
    assert not errors

def test_validator_delegates_to_pydantic_for_severity_enum(base_valid_finding):
    """Asserts that invalid severity enum values are caught by Pydantic schema validation."""
    base_valid_finding["severity"] = "banana"
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert any("Schema validation failed" in err for err in errors)

def test_validator_does_not_block_correctness_claims_mentioning_security_or_passwords(base_valid_finding):
    """
    Asserts that legitimate correctness/spec-divergence findings containing security
    or credential-related terms (e.g. password, circular dependency) are NOT blocked.
    Topic filtering is the job of prompt engineering, not keyword substring bans.
    """
    # 1. Spec-code mismatch regarding password length rule
    base_valid_finding["claim"] = "SPEC requires password length >= 8 but code checks >= 6"
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert not errors

    # 2. Spec-code divergence regarding circular dependency
    base_valid_finding["claim"] = "circular dependency on module X violating spec layering"
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert not errors

    # 3. Spec-code divergence regarding security headers
    base_valid_finding["claim"] = "spec mandates security headers but handler omits them"
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert not errors

def test_validator_enforces_coordinate_format(base_valid_finding):
    """Asserts that location and evidence_ref formats are validated."""
    base_valid_finding["location"] = "invalid-location"
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert any("Schema validation failed" in err for err in errors)
    
    base_valid_finding["location"] = {
        "path": "app.py",
        "line_start": -5,
        "line_end": 10
    }
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert any("Schema validation failed" in err for err in errors)

    base_valid_finding["location"] = {
        "path": "app.py",
        "line_start": 10,
        "line_end": 5
    }
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert any("Schema validation failed" in err for err in errors)

    # Test evidence_ref formatting
    base_valid_finding["location"] = {
        "path": "app.py",
        "line_start": 10,
        "line_end": 15
    }
    base_valid_finding["evidence_ref"] = ["SPEC.md"]  # missing file: and line numbers
    errors = validate_correctness_finding(base_valid_finding, has_spec=True)
    assert any("Invalid evidence_ref format" in err for err in errors)
