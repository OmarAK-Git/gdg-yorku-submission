# Review

## Spec compliance review

- Anchors include `perspective` (`source_agent:perspective:path:line:rule:symbol`), preventing cross-perspective merges.
- Cross-perspective and cross-source agent merges are strictly blocked inside `merge_finding_objects`, throwing a ValueError if attempted.
- Numeric offsets (like `token_offset` / `offset`) are sorted numerically in `parse_discriminator_for_sorting` (e.g. `20` before `100`).
- Falsy offsets (like `0`) are correctly preserved using strict `is not None` metadata value checks.
- LLM findings with identical claims are kept distinct and assigned separate ordinals, in compliance with "claim-hash ordinals".
- Semantic properties and original input indices are used to stably sort the output findings list, offering complete determinism across all permutations.
- Merged provisional IDs are preserved in metadata (`merged_from_provisional`) on finalized findings.

## Code quality review

- Key contracts for rule, sub-rule, stable symbol, and discriminator are aligned and documented.
- Status merging follows correct priority precedence: `active` > `contested` > `advisory`.
- Robust type safety and list flattening for provisional ID mapping.

## Risk review

- Completely eliminates any risk of hidden omissions by ensuring LLM findings do not collapse, cross-perspective issues do not merge, and numeric offsets sort correctly.

## Human review notes

- All tests run and pass. Property-style conservation tests verify `union(id_map.values()) == input_ids` and total count 1:1 matching.
