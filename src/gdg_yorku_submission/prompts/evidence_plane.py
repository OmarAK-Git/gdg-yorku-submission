import re
import secrets
from typing import Dict, Tuple, Optional
from gdg_yorku_submission.schemas import CorpusFile
from gdg_yorku_submission.corpus import get_prompt_corpus

def sanitize_path(path: str) -> str:
    """
    Sanitizes untrusted file paths to prevent quote/tag escaping and newlines.
    Strips non-printable control characters and escapes quotes and brackets.
    """
    if not path:
        return ""
    # Strip control characters (newlines, returns, tabs, etc.)
    clean_path = "".join(c for c in path if c.isprintable())
    # Escape quotes and tag brackets
    return clean_path.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')

def sanitize_file_content(content: str, nonce: str) -> str:
    """
    Sanitizes untrusted file content to prevent escaping from the evidence plane.
    Replaces any occurrences of the nonce with [NONCE_REDACTED] and neutralizes
    evidence_plane and file tags.
    """
    if not content:
        return ""
    
    # Redact any literal occurrences of the nonce to prevent leakage or guessing
    if nonce:
        content = content.replace(nonce, "[NONCE_REDACTED]")
    
    # Escape tag structures case-insensitively to prevent breakout
    content = re.sub(r'</?evidence_plane\b', lambda m: m.group(0).replace('<', '&lt;'), content, flags=re.IGNORECASE)
    content = re.sub(r'</?file\b', lambda m: m.group(0).replace('<', '&lt;'), content, flags=re.IGNORECASE)
    
    return content

def build_evidence_plane(corpus: Dict[str, CorpusFile], nonce: str) -> str:
    """
    Constructs the isolated evidence plane block from the prompt-exposed corpus files.
    Only prompt_exposed files are formatted; others are skipped.
    
    PRECONDITION: The corpus files' `redacted_text` must already be processed by the 
    secret scanning and redaction preflight gate. This function relies on and consumes 
    `redacted_text` directly to guarantee no raw secrets leak into the LLM context.
    """
    prompt_corpus = get_prompt_corpus(corpus)
    
    lines = []
    lines.append(f'<evidence_plane nonce="{nonce}">')
    
    # Sort paths for deterministic prompt output order
    sorted_paths = sorted(prompt_corpus.keys())
    for path in sorted_paths:
        file_obj = prompt_corpus[path]
        
        # Ensure we only use redacted_text (Precondition requirement)
        sanitized_text = sanitize_file_content(file_obj.redacted_text, nonce)
        sanitized_path = sanitize_path(file_obj.normalized_path)
        lines.append(f'<file nonce="{nonce}" path="{sanitized_path}">')
        lines.append(sanitized_text)
        lines.append(f'</file nonce="{nonce}">')
        
    lines.append(f'</evidence_plane nonce="{nonce}">')
    return "\n".join(lines)

def build_evidence_plane_prompt(
    corpus: Dict[str, CorpusFile],
    instructions: str,
    nonce: Optional[str] = None
) -> Tuple[str, str]:
    """
    Constructs the full prompt by combining trusted instructions and the nonced evidence plane.
    Generates a cryptographically secure random nonce if none is provided.
    
    PRECONDITION: The corpus files' `redacted_text` must already be processed by the 
    secret scanning and redaction preflight gate.
    
    Returns:
        A tuple of (prompt_text, nonce)
    """
    if not nonce:
        nonce = secrets.token_hex(16)
        
    evidence_block = build_evidence_plane(corpus, nonce)
    
    # Clean join of instructions and evidence plane block
    prompt_text = f"{instructions.strip()}\n\n{evidence_block}"
    return prompt_text, nonce
