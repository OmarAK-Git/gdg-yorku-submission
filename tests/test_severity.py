import pytest
from gdg_yorku_submission.severity import Severity, SEVERITY_FLOOR, map_severity, is_at_or_above_floor

def test_severity_values():
    assert Severity.CRITICAL == "critical"
    assert Severity.HIGH == "high"
    assert Severity.MEDIUM == "medium"
    assert Severity.LOW == "low"
    assert Severity.INFO == "info"

def test_severity_floor():
    assert SEVERITY_FLOOR == Severity.HIGH

def test_map_severity_success():
    # Legacy mappings
    assert map_severity("blocker") == Severity.CRITICAL
    assert map_severity("BLOCKER ") == Severity.CRITICAL
    assert map_severity("security-blocker") == Severity.HIGH
    assert map_severity("security_blocker") == Severity.HIGH
    assert map_severity("major") == Severity.MEDIUM
    assert map_severity("minor") == Severity.LOW
    assert map_severity("observational") == Severity.INFO
    assert map_severity("hygiene") == Severity.INFO

    # Standard mappings
    assert map_severity("critical") == Severity.CRITICAL
    assert map_severity("high") == Severity.HIGH
    assert map_severity("medium") == Severity.MEDIUM
    assert map_severity("low") == Severity.LOW
    assert map_severity("info") == Severity.INFO

def test_map_severity_failures():
    with pytest.raises(ValueError, match="Unknown raw severity"):
        map_severity("unknown")
    with pytest.raises(ValueError, match="Unknown raw severity"):
        map_severity("")
    with pytest.raises(ValueError, match="Severity must be a string"):
        map_severity(None)  # type: ignore
    with pytest.raises(ValueError, match="Severity must be a string"):
        map_severity(123)  # type: ignore

def test_is_at_or_above_floor():
    assert is_at_or_above_floor(Severity.CRITICAL) is True
    assert is_at_or_above_floor(Severity.HIGH) is True
    assert is_at_or_above_floor(Severity.MEDIUM) is False
    assert is_at_or_above_floor(Severity.LOW) is False
    assert is_at_or_above_floor(Severity.INFO) is False

def test_severity_comparisons():
    # Verify that string-comparisons like alphabetically "medium" > "high"
    # are overridden by our ranking comparison.
    assert Severity.MEDIUM < Severity.HIGH
    assert Severity.MEDIUM <= Severity.HIGH
    assert not (Severity.MEDIUM >= Severity.HIGH)
    assert not (Severity.MEDIUM > Severity.HIGH)
    
    assert Severity.CRITICAL > Severity.HIGH
    assert Severity.CRITICAL >= Severity.HIGH
    assert not (Severity.CRITICAL <= Severity.HIGH)
    assert not (Severity.CRITICAL < Severity.HIGH)
    
    assert Severity.HIGH >= Severity.HIGH
    assert Severity.HIGH <= Severity.HIGH
    assert not (Severity.HIGH > Severity.HIGH)
    assert not (Severity.HIGH < Severity.HIGH)
    
    # Compare enums
    assert Severity.INFO < Severity.LOW < Severity.MEDIUM < Severity.HIGH < Severity.CRITICAL

    # Mixed comparisons with raw strings (coerced automatically)
    assert Severity.MEDIUM < "high"
    assert Severity.MEDIUM <= "high"
    assert not (Severity.MEDIUM >= "high")
    assert not (Severity.MEDIUM > "high")

    assert Severity.CRITICAL > "high"
    assert Severity.CRITICAL >= "high"
    assert not (Severity.CRITICAL <= "high")
    assert not (Severity.CRITICAL < "high")

    # Invalid type fallback comparison raises TypeError
    with pytest.raises(TypeError):
        Severity.MEDIUM < 123  # type: ignore
