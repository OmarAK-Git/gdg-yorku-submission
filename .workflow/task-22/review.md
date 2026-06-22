# Review - Task 22 Revisions

## Spec compliance review
- **Production HTTP Client Path**: Added `test_orbit_client_query_symbol_real_http` mocking `urllib.request.urlopen` directly, verifying URL, query parameters, header attributes (`Authorization`, `X-Orbit-Token`, `Accept`), and Pydantic model mapping.
- **Severity Cap**: Implemented a cap in `agent.py` setting `severity = min(severity, Severity.MEDIUM)`. This keeps all blast-radius findings below the floor, allowing the coordinator to merge or omit them.
- **Deduplication, Caching & Performance budget**: deduplicated symbols across files, introduced an in-memory query cache, capped queries at 20 unique symbols per run, and limited the total query time to a 2.0s elapsed wall-clock time limit.
- **Redaction Line-Map**: Wired `cf.map_line(redacted_line)` to map coordinates to original file coordinate systems, with out-of-bounds skipping.
- **Claims & Symbol Duplicates**: Fixed bare trailing colons for dependencies-only claims, and filtered extracted symbols to only keep the single most-qualified (longest name string length) symbol per line.

## Code quality review
- Added explicit `import urllib.parse` in `orbit_client.py`.
- The test suite is fast, deterministic, and self-contained.

## Risk review
- **Line-map contract safety**: Validated via a custom test with a non-identity map `{1:1, 2:5}` ensuring coordinates align properly.
- **Slow APIs**: Checked wall-clock timer budget to avoid blocking FastAPI threads.
