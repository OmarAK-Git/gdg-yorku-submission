import hashlib
import uuid
from typing import Dict, List, Any

class RedactionContext:
    def __init__(self, salt: bytes = None) -> None:
        # Generate a per-run random salt if not provided
        self.salt = salt or uuid.uuid4().bytes
        # Map of raw secrets to their placeholders
        self.secrets_to_placeholders: Dict[str, str] = {}
        # Map of raw secrets to their fingerprints
        self.secrets_to_fingerprints: Dict[str, str] = {}
        # Sorted list of raw secrets by length descending to prevent partial match issues
        self.sorted_raw_secrets: List[str] = []

    def get_fingerprint(self, secret: str) -> str:
        """
        Computes a truncated salted hash fingerprint.
        A last-4 substring is appended only for values >= 20 characters;
        otherwise it is hash-only.
        """
        if not secret:
            return ""
        if secret in self.secrets_to_fingerprints:
            return self.secrets_to_fingerprints[secret]

        h = hashlib.sha256()
        h.update(self.salt)
        h.update(secret.encode("utf-8", errors="replace"))
        hash_hex = h.hexdigest()[:16]

        if len(secret) >= 20:
            last_4 = secret[-4:]
            fp = f"sha256_{hash_hex}_{last_4}"
        else:
            fp = f"sha256_{hash_hex}"

        self.secrets_to_fingerprints[secret] = fp
        return fp

    def register_secret(self, secret: str, secret_type: str = "SECRET") -> str:
        """
        Registers a raw secret value, determines its fingerprint,
        and generates a safe placeholder.
        """
        if not secret:
            return ""
        if secret in self.secrets_to_placeholders:
            return self.secrets_to_placeholders[secret]

        fp = self.get_fingerprint(secret)
        # Create placeholder
        clean_type = secret_type.upper().replace(" ", "_")
        placeholder = f"[REDACTED_{clean_type}_{fp}]"
        
        self.secrets_to_placeholders[secret] = placeholder
        self.sorted_raw_secrets = sorted(self.secrets_to_placeholders.keys(), key=len, reverse=True)
        return placeholder

    def redact(self, text: str) -> str:
        """
        Redacts all registered secrets from the given text.
        Replaces each raw secret with its registered placeholder.
        Pads multi-line placeholders with newlines to preserve the original line count (R5).
        
        Note: The redaction invariant is scoped to secrets that have been explicitly
        detected and registered in this RedactionContext.
        """
        if not text or not isinstance(text, str):
            return text

        redacted_text = text
        for secret in self.sorted_raw_secrets:
            placeholder = self.secrets_to_placeholders[secret]
            # Count newlines in the original secret to pad the placeholder and preserve line count (BUG-002)
            num_newlines = secret.count('\n')
            if num_newlines > 0:
                newline_char = "\r\n" if "\r\n" in secret else "\n"
                padded_placeholder = placeholder + (newline_char * num_newlines)
            else:
                padded_placeholder = placeholder
            redacted_text = redacted_text.replace(secret, padded_placeholder)

        return redacted_text

    def redact_exception(self, exc: Exception) -> Exception:
        """
        Returns a new exception of the same type with its args, __cause__,
        and __context__ recursively redacted.
        
        Note: Chained traceback frames are not directly modified; tracebacks should
        be passed through redact() before being written to any log or external sink.
        """
        if not exc:
            return exc
        
        # Redact args recursively
        redacted_args = tuple(
            self.redact(arg) if isinstance(arg, str)
            else sanitize_value(arg, self)
            for arg in exc.args
        )
        
        # Recursively redact chained exceptions
        cause = None
        if exc.__cause__:
            cause = self.redact_exception(exc.__cause__)
        context = None
        if exc.__context__:
            context = self.redact_exception(exc.__context__)
            
        try:
            new_exc = type(exc)(*redacted_args)
            new_exc.__cause__ = cause
            new_exc.__context__ = context
            return new_exc
        except Exception:
            new_exc = Exception(*redacted_args)
            new_exc.__cause__ = cause
            new_exc.__context__ = context
            return new_exc


GLOBAL_REDACTION_CONTEXT = RedactionContext()


def redact(text: str) -> str:
    """Convenience helper to redact text using the global context."""
    return GLOBAL_REDACTION_CONTEXT.redact(text)


def register_secret(secret: str, secret_type: str = "SECRET") -> str:
    """Convenience helper to register a secret using the global context."""
    return GLOBAL_REDACTION_CONTEXT.register_secret(secret, secret_type)


def sanitize_value(val: Any, context: RedactionContext = None) -> Any:
    """
    Recursively sanitizes values (str, dict, list, exception) to redact secrets.
    """
    if context is None:
        context = GLOBAL_REDACTION_CONTEXT

    if isinstance(val, str):
        return context.redact(val)
    elif isinstance(val, dict):
        return {k: sanitize_value(v, context) for k, v in val.items()}
    elif isinstance(val, list):
        return [sanitize_value(v, context) for v in val]
    elif isinstance(val, Exception):
        return context.redact_exception(val)
    else:
        return val
