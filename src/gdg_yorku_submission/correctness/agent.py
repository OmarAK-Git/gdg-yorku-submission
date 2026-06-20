import json
import logging
from typing import List, Tuple, Dict, Any, Callable, Optional
from gdg_yorku_submission.schemas import ReviewFinding, Location, CorpusFile
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.correctness.sot import discover_sot
from gdg_yorku_submission.correctness.methodology import load_methodology, validate_correctness_finding
from gdg_yorku_submission.prompts.evidence_plane import build_evidence_plane_prompt
from gdg_yorku_submission.budget import acquire_budget_lease, BudgetLease, BudgetExhaustedError
from gdg_yorku_submission.llm.gemini import GeminiClient

logger = logging.getLogger(__name__)

class CorrectnessAgentException(Exception):
    """Custom exception class for Correctness Agent failures."""
    pass

def run_correctness_review(
    orch,
    gemini_client: Optional[GeminiClient] = None
) -> Tuple[List[ReviewFinding], str, str]:
    """
    Runs the correctness review perspective.
    1. Discovers the Source of Truth. If absent, skips and returns no-spec status.
    2. Builds the evidence-plane prompt (redacted corpus files + SoT).
    3. Acquires budget lease.
    4. Calls Gemini to generate findings.
    5. Parses, validates, and cleans findings before writing to orchestrator state.
    """
    corpus = orch.get_corpus()
    
    # 1. Discover SoT
    sot_result = discover_sot("", corpus=corpus)
    if sot_result.status == "no_spec_found_conformance_skipped":
        # Check if we should also run logic consistency checks if instructed,
        # but spec says: "emits explicit no_spec_found_conformance_skipped otherwise"
        # We skipped the correctness review.
        return [], "skipped", "no_spec_found_conformance_skipped"

    # We found a specification
    sot_path = sot_result.sot_path
    
    # 2. Build nonced evidence-plane prompt
    methodology_text = load_methodology()
    
    # Include instructions requesting structured JSON output conforming to schemas
    instructions = (
        f"{methodology_text}\n\n"
        "You MUST analyze the implementation files in the evidence plane against the discovered specification file "
        f"('{sot_path}'). Identify all code-specification divergences, design inconsistencies, or intent mismatches.\n"
        "Tone must be direction-neutral (do not assume either the spec or the code is wrong).\n\n"
        "You MUST return a JSON list of findings. Do not include any markdown fences or explanatory text. "
        "The response must be a JSON array where each object has this structure:\n"
        "[\n"
        "  {\n"
        "    \"id\": \"prov-correctness-<unique-index>\",\n"
        "    \"source_agent\": \"correctness_agent\",\n"
        "    \"perspective\": \"correctness\",\n"
        "    \"severity\": \"critical|high|medium|low|info\",\n"
        "    \"location\": { \"path\": \"<relative-file-path>\", \"line_start\": <int>, \"line_end\": <int> },\n"
        "    \"claim\": \"<direction-neutral claim narrative>\",\n"
        "    \"evidence_ref\": [\"file:<sot-file-path>#<line_start>-<line_end>\", \"file:<code-file-path>#<line_start>-<line_end>\"]\n"
        "  }\n"
        "]\n"
        "Make sure location and evidence_ref coordinates are valid and present in the source files."
    )
    
    prompt_text, nonce = build_evidence_plane_prompt(corpus, instructions)
    
    # 4. Call Gemini client with retries (Lease is checked inside generate_content)
    if gemini_client is None:
        gemini_client = GeminiClient()
        
    # Bounded retry loop for malformed JSON responses
    max_retries = 2
    raw_response = ""
    parsed_findings = None
    
    # Calculate estimated tokens including both input & output for lease accuracy (Issue 8)
    estimated_input_tokens = len(prompt_text) // 4 + 1000
    estimated_output_tokens = 500
    
    for attempt in range(max_retries):
        try:
            raw_response = gemini_client.generate_content(
                orch,
                prompt=prompt_text,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=estimated_output_tokens,
                component="correctness_agent"
            )
            
            # Clean response text from markdown code blocks if any
            cleaned_text = raw_response.strip()
            if cleaned_text.startswith("```"):
                # strip code block formatting
                lines = cleaned_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned_text = "\n".join(lines).strip()
                
            parsed_findings = json.loads(cleaned_text)
            if not isinstance(parsed_findings, list):
                raise ValueError("Response is not a JSON list")
            break
        except BudgetExhaustedError as e:
            logger.error(f"Budget lease acquisition failed: {e}")
            # Emit a stable reason code instead of free text (Issue 3)
            return [], "failed", "budget_exhausted"
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == max_retries - 1:
                raise CorrectnessAgentException(
                    f"Gemini client returned invalid JSON after {max_retries} attempts. Response: {raw_response[:200]}"
                ) from e
            logger.warning(f"Malformed JSON on attempt {attempt + 1}: {e}. Retrying...")
            
    # 5. Validate and filter findings
    valid_findings: List[ReviewFinding] = []
    
    for idx, raw_finding in enumerate(parsed_findings):
        # Enforce schemas, source agents, severity caps, coordinate checks
        errors = validate_correctness_finding(raw_finding, has_spec=True)
        if errors:
            logger.warning(f"Finding at index {idx} failed validation: {errors}. Skipping.")
            continue
            
        # Grounding check: Require >= 1 evidence_ref and at least one must cite the discovered sot_path (Issue 4)
        evidence_refs = raw_finding.get("evidence_ref", [])
        if not evidence_refs:
            logger.warning(f"Finding at index {idx} has empty evidence_ref. Skipping.")
            continue
            
        cites_sot = False
        normalized_sot_path = sot_path.replace("\\", "/").lower()
        for ref in evidence_refs:
            if not ref.startswith("file:"):
                continue
            ref_path = ref.split("#")[0][5:]
            if ref_path.replace("\\", "/").lower() == normalized_sot_path:
                cites_sot = True
                break
                
        if not cites_sot:
            logger.warning(f"Finding at index {idx} does not cite SoT path '{sot_path}'. Skipping.")
            continue

        # Syntactic coordinate existence check:
        # We ensure location.path exists in the corpus and line numbers are valid.
        loc = raw_finding["location"]
        path = loc["path"]
        
        # Look for path case-insensitively in corpus
        corpus_key = None
        for k in corpus.keys():
            if k.lower() == path.replace("\\", "/").lower():
                corpus_key = k
                break
                
        if corpus_key is None:
            logger.warning(f"Finding location path '{path}' does not exist in corpus. Skipping.")
            continue
            
        corpus_file = corpus[corpus_key]
        
        # Translate location line numbers from redacted to original coordinates (Issue 5)
        loc_start_redacted = loc["line_start"]
        loc_end_redacted = loc["line_end"]
        loc_start_original = corpus_file.map_line(loc_start_redacted)
        loc_end_original = corpus_file.map_line(loc_end_redacted)
        
        # Enforce existence boundaries and ordering (Issue 5 & 6)
        if loc_start_original < 1 or loc_end_original < 1 or loc_start_original > corpus_file.original_line_count or loc_end_original > corpus_file.original_line_count or loc_end_original < loc_start_original:
            logger.warning(
                f"Finding location lines ({loc_start_original}-{loc_end_original}) out of bounds or invalid "
                f"for '{path}' (original line count: {corpus_file.original_line_count}). Skipping."
            )
            continue
            
        # Update loc with original coordinates
        loc["line_start"] = loc_start_original
        loc["line_end"] = loc_end_original
            
        # Verify and map evidence_refs coordinates as well
        evidence_refs_valid = True
        mapped_evidence_refs = []
        for ref in evidence_refs:
            ref_parts = ref.split("#")
            ref_file_prefix = ref_parts[0]
            ref_path = ref_file_prefix[5:] # strip "file:"
            ref_lines = ref_parts[1].split("-")
            ref_start_redacted, ref_end_redacted = int(ref_lines[0]), int(ref_lines[1])
            
            ref_corpus_key = None
            for k in corpus.keys():
                if k.lower() == ref_path.replace("\\", "/").lower():
                    ref_corpus_key = k
                    break
                    
            if ref_corpus_key is None:
                logger.warning(f"Finding evidence path '{ref_path}' does not exist in corpus. Skipping.")
                evidence_refs_valid = False
                break
                
            ref_file = corpus[ref_corpus_key]
            
            # Translate evidence line numbers from redacted to original coordinates (Issue 5)
            ref_start_original = ref_file.map_line(ref_start_redacted)
            ref_end_original = ref_file.map_line(ref_end_redacted)
            
            # Enforce 1 <= ref_start_original <= ref_end_original <= original_line_count (Issue 6)
            if ref_start_original < 1 or ref_end_original < 1 or ref_start_original > ref_file.original_line_count or ref_end_original > ref_file.original_line_count or ref_end_original < ref_start_original:
                logger.warning(
                    f"Finding evidence lines ({ref_start_original}-{ref_end_original}) out of bounds or invalid "
                    f"for '{ref_path}' (original line count: {ref_file.original_line_count}). Skipping."
                )
                evidence_refs_valid = False
                break
                
            mapped_evidence_refs.append(f"{ref_file_prefix}#{ref_start_original}-{ref_end_original}")
                
        if not evidence_refs_valid:
            continue
            
        # Finding is fully valid, build ReviewFinding
        valid_finding = ReviewFinding(
            id=raw_finding["id"],
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity(raw_finding["severity"]),
            location=Location(**loc),
            claim=raw_finding["claim"],
            evidence_ref=mapped_evidence_refs,
            status=raw_finding.get("status", "active"),
            metadata=raw_finding.get("metadata", {})
        )
        valid_findings.append(valid_finding)
        
    return valid_findings, "complete", ""

def make_correctness_specialist(
    orch,
    gemini_client: Optional[GeminiClient] = None
) -> Callable[[], Tuple[List[ReviewFinding], str, str]]:
    """
    Returns the correctness specialist Callable.
    """
    return lambda: run_correctness_review(orch, gemini_client=gemini_client)
