import os
from pathlib import Path
from typing import Optional, Dict, Literal, Tuple
from pydantic import BaseModel, Field, ConfigDict

from gdg_yorku_submission.schemas import CorpusFile

class SotDiscoveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sot_text: Optional[str] = Field(None, description="The text content of the discovered Source of Truth")
    sot_path: Optional[str] = Field(None, description="The normalized path relative to workspace root")
    source_type: Optional[Literal["root_spec", "root_design", "readme_sections", "docs_spec"]] = Field(None, description="Type of the SoT source")
    status: Literal["found", "no_spec_found_conformance_skipped"] = Field("no_spec_found_conformance_skipped", description="Status of the discovery")

def parse_markdown_headings(line: str) -> Optional[int]:
    """
    Returns the heading level (1 or 2) if it is an H1 or H2, otherwise None.
    Heading syntax matches '#' or '##' followed by whitespace or end of line.
    """
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    
    hash_count = 0
    for char in stripped:
        if char == '#':
            hash_count += 1
        else:
            break
            
    if hash_count > 0 and (hash_count == len(stripped) or stripped[hash_count].isspace()):
        return hash_count
    return None

def extract_readme_sections(readme_text: str) -> str:
    """
    Extracts content under allowlisted H2 sections: ## Spec, ## Design, ## Requirements, ## Intent.
    Extraction terminates at any H1 (#) or non-allowed H2 (##) heading.
    Supports tracking code blocks to avoid treating comments like '# comment' as headings.
    """
    lines = readme_text.splitlines(keepends=True)
    extracted_lines = []
    in_extraction_mode = False
    in_code_block = False
    
    for line in lines:
        stripped = line.strip()
        
        # Check code block toggle (triple backticks)
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            
        if not in_code_block:
            level = parse_markdown_headings(line)
            if level == 1:
                in_extraction_mode = False
            elif level == 2:
                # Get heading content after '##'
                remainder = stripped[2:].strip().lower()
                if remainder in {"spec", "design", "requirements", "intent"}:
                    in_extraction_mode = True
                else:
                    in_extraction_mode = False
                    
        if in_extraction_mode:
            extracted_lines.append(line)
            
    return "".join(extracted_lines)

def _find_in_corpus(
    target_rel_path: str,
    corpus: Dict[str, CorpusFile]
) -> Optional[Tuple[str, str]]:
    """
    Looks for target_rel_path case-insensitively in the corpus.
    To prevent filesystem leaks and enforce the trust boundary, this function
    ONLY queries the provided corpus dictionary.
    Returns (redacted_text, key) or None.
    """
    if corpus is None:
        raise ValueError("corpus is required and cannot be None")
        
    target_normalized = target_rel_path.replace("\\", "/").lower()
    
    matches = []
    for key, corpus_file in corpus.items():
        if key.lower() == target_normalized:
            # SoT selection must be restricted to prompt_exposed files (Finding 4)
            if corpus_file.exposure_status == "prompt_exposed":
                # Ensure the file has non-empty/non-whitespace text (Finding 5)
                if corpus_file.redacted_text.strip():
                    matches.append((key, corpus_file))
                    
    if not matches:
        return None
        
    # Deterministic tie-breaker for case-collisions (Finding 6)
    matches.sort(key=lambda x: x[0])
    key, corpus_file = matches[0]
    
    if corpus_file.ingest_status == "success":
        # Enforce the redaction invariant precondition (Finding 2)
        if not corpus_file.redaction_applied:
            raise RuntimeError(
                f"Precondition violated: secret scanning was not applied to {key} "
                f"before Source-of-Truth discovery."
            )
        return corpus_file.redacted_text, key
    else:
        return None

def discover_sot(
    workspace_dir: str,
    corpus: Optional[Dict[str, CorpusFile]] = None
) -> SotDiscoveryResult:
    """
    Discovers the Source-of-Truth file(s) in the corpus.
    Order of precedence:
      1. Root SPEC.md
      2. Root DESIGN.md
      3. README intent sections (selected only via heading allowlist: ## Spec, ## Design, ## Requirements, ## Intent)
      4. conventional docs/SPEC.md
    Absent -> no-spec fallback status: no_spec_found_conformance_skipped.

    NOTE: workspace_dir is retained solely for signature compatibility with Orchestrator/Task 12,
    but is unused since all file discovery is resolved entirely from the in-memory corpus.
    """
    if corpus is None:
        raise ValueError("corpus is required and cannot be None")

    # 1. Check root SPEC.md
    res = _find_in_corpus("SPEC.md", corpus)
    if res is not None:
        content, path = res
        return SotDiscoveryResult(
            sot_text=content,
            sot_path=path,
            source_type="root_spec",
            status="found"
        )
        
    # 2. Check root DESIGN.md
    res = _find_in_corpus("DESIGN.md", corpus)
    if res is not None:
        content, path = res
        return SotDiscoveryResult(
            sot_text=content,
            sot_path=path,
            source_type="root_design",
            status="found"
        )
        
    # 3. Check README intent sections
    # Try both README.md and README
    readme_res = _find_in_corpus("README.md", corpus)
    if readme_res is None:
        readme_res = _find_in_corpus("README", corpus)
        
    if readme_res is not None:
        content, path = readme_res
        extracted = extract_readme_sections(content)
        if extracted.strip():
            return SotDiscoveryResult(
                sot_text=extracted,
                sot_path=path,
                source_type="readme_sections",
                status="found"
            )
            
    # 4. Check docs/SPEC.md
    res = _find_in_corpus("docs/SPEC.md", corpus)
    if res is not None:
        content, path = res
        return SotDiscoveryResult(
            sot_text=content,
            sot_path=path,
            source_type="docs_spec",
            status="found"
        )
        
    # 5. Fallback
    return SotDiscoveryResult(
        sot_text=None,
        sot_path=None,
        source_type=None,
        status="no_spec_found_conformance_skipped"
    )
