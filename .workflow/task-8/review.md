# Review

## Spec compliance review
- Verified that trusted instructions stay separate from untrusted content.
- Verified that a per-run random nonce is used for the outer evidence plane delimiters and the inner file boundary tags (`<file nonce="...">` and `</file nonce="...">`) to close injection seams.
- Verified that only `prompt_exposed` files are formatted.
- Verified that only `redacted_text` enters the prompt, with an explicit docstring precondition note for callers.
- Verified that the `normalized_path` is sanitized to strip control characters and escape HTML/XML characters, preventing quote breakout and path injection.
- Verified line count conservation (R5) using explicit test assertions.

## Code quality review
- Implemented robust tag neutralizing (replacing `<` with `&lt;` case-insensitively for delimiter tags) in the file content.
- Implemented path sanitization for safety against zip files containing hostile entry names (quotes, newlines, tag brackets).
- Standard python typing is used.

## Risk review
- Added unguessability/negative breakout tests where the attacker tries to close the evidence plane using a guessed nonce, proving that only the builder's actual closing tag (using the dynamic random nonce) is recognized.
- Checked shuffled key insertion order determinism and reproducibility.
