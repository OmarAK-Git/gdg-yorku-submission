from enum import Enum
from typing import Any

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        """Returns integer ranking of severity (higher is more severe)."""
        ranks = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }
        return ranks.get(self, 0)

    def _coerce_other(self, other: Any) -> Any:
        if isinstance(other, str) and not isinstance(other, Severity):
            try:
                return Severity(other)
            except ValueError:
                pass
        return other

    def __lt__(self, other: Any) -> bool:
        other = self._coerce_other(other)
        if not isinstance(other, Severity):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other: Any) -> bool:
        other = self._coerce_other(other)
        if not isinstance(other, Severity):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other: Any) -> bool:
        other = self._coerce_other(other)
        if not isinstance(other, Severity):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other: Any) -> bool:
        other = self._coerce_other(other)
        if not isinstance(other, Severity):
            return NotImplemented
        return self.rank >= other.rank

# Canonical floor severity
SEVERITY_FLOOR = Severity.HIGH

def map_severity(raw_severity: str) -> Severity:
    """
    Maps legacy/divergent client labels to standardized enums.
    
    Mapping table:
    - blocker -> critical
    - security-blocker -> high
    - major -> medium
    - minor -> low
    - observational / hygiene -> info
    
    Deliberate leniency:
    - Normalizes underscores to hyphens (e.g. "security_blocker" -> "security-blocker").
    - Supports mapping standard canonical values to themselves (e.g. "high" -> Severity.HIGH).
    - Performs case-insensitive matching and strips surrounding whitespace.
    
    Raises ValueError for unrecognized values.
    """
    if not isinstance(raw_severity, str):
        raise ValueError(f"Severity must be a string, got {type(raw_severity)}")
        
    normalized = raw_severity.strip().lower().replace("_", "-")
    
    mapping = {
        "blocker": Severity.CRITICAL,
        "security-blocker": Severity.HIGH,
        "major": Severity.MEDIUM,
        "minor": Severity.LOW,
        "observational": Severity.INFO,
        "hygiene": Severity.INFO,
        
        # Standard values are mapped to themselves
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }
    
    if normalized not in mapping:
        raise ValueError(f"Unknown raw severity: {raw_severity}")
        
    return mapping[normalized]

def is_at_or_above_floor(severity: Severity) -> bool:
    """
    Returns True if the severity is at or above the reporting floor (high).
    """
    return severity >= SEVERITY_FLOOR
