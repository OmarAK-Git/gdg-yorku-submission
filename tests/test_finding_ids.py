import pytest
import hashlib
from gdg_yorku_submission.schemas import Location, Finding, ReportFinding
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.finding_ids import (
    compute_anchor,
    finalize_finding_ids,
    parse_discriminator_for_sorting,
)


def test_anchor_generation_determinism_and_normalization():
    # Same parameters must produce same anchor
    loc1 = Location(path="src/main.py", line_start=10, line_end=15)
    f1 = Finding(
        id="prov1",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc1,
        claim="SQL Injection",
        metadata={"rule": "sqli", "symbol": "db_execute"}
    )
    
    anchor1 = compute_anchor(f1)
    
    # Path normalization (backslash normalization)
    loc2 = Location(path="src\\main.py", line_start=10, line_end=15)
    f2 = Finding(
        id="prov2",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc2,
        claim="SQL Injection but different prose",
        metadata={"rule_or_category": "sqli", "stable_symbol": "db_execute"}
    )
    
    anchor2 = compute_anchor(f2)
    assert anchor1 == anchor2
    
    # Different agent -> different anchor
    f3 = f1.model_copy(update={"source_agent": "security_debate"})
    assert compute_anchor(f3) != anchor1
    
    # Different perspective -> different anchor (Gap 2)
    f_persp = f1.model_copy(update={"perspective": "preflight"})
    assert compute_anchor(f_persp) != anchor1
    
    # Different line_start -> different anchor
    f4 = f1.model_copy(update={"location": Location(path="src/main.py", line_start=11, line_end=15)})
    assert compute_anchor(f4) != anchor1
    
    # Different rule_or_category -> different anchor
    f5 = f1.model_copy(update={"metadata": {"rule": "xss", "symbol": "db_execute"}})
    assert compute_anchor(f5) != anchor1


def test_finalize_single_finding_prose_independence():
    loc = Location(path="app.py", line_start=5, line_end=5)
    f_run1 = Finding(
        id="prov-a",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.MEDIUM,
        location=loc,
        claim="Method signature mismatch with spec",
    )
    
    f_run2 = Finding(
        id="prov-b",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.MEDIUM,
        location=loc,
        claim="Spec says X, but code has Y",
    )
    
    finalized1, map1 = finalize_finding_ids([f_run1])
    finalized2, map2 = finalize_finding_ids([f_run2])
    
    assert len(finalized1) == 1
    assert len(finalized2) == 1
    
    # Both should get the same ID because they have the same anchor and both are the only finding in their group
    assert finalized1[0].id == finalized2[0].id
    assert map1[finalized1[0].id] == ["prov-a"]
    assert map2[finalized2[0].id] == ["prov-b"]
    
    # Prove that different anchors produce different IDs (Gap 8)
    f_diff = f_run1.model_copy(update={"location": Location(path="other.py", line_start=99, line_end=99)})
    finalized3, _ = finalize_finding_ids([f_diff])
    assert finalized1[0].id != finalized3[0].id


def test_finalize_multiple_findings_distinct_stable_ids_and_permutations():
    loc = Location(path="app.py", line_start=20, line_end=20)
    
    # Two distinct LLM findings at same line, same category
    f1 = Finding(
        id="prov1",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.MEDIUM,
        location=loc,
        claim="Divergence alpha",
    )
    
    f2 = Finding(
        id="prov2",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.MEDIUM,
        location=loc,
        claim="Divergence beta",
    )
    
    # Order of inputs shouldn't change final stable IDs (Gap 10)
    finalized_a, map_a = finalize_finding_ids([f1, f2])
    finalized_b, map_b = finalize_finding_ids([f2, f1])
    
    assert len(finalized_a) == 2
    assert len(finalized_b) == 2
    
    # Map from finalized ID to constituent provisional IDs should match
    # Verify per-finding stability across permutations
    finalized_f1_a = next(f for f in finalized_a if "prov1" in map_a[f.id])
    finalized_f1_b = next(f for f in finalized_b if "prov1" in map_b[f.id])
    assert finalized_f1_a.id == finalized_f1_b.id
    
    finalized_f2_a = next(f for f in finalized_a if "prov2" in map_a[f.id])
    finalized_f2_b = next(f for f in finalized_b if "prov2" in map_b[f.id])
    assert finalized_f2_a.id == finalized_f2_b.id


def test_finalize_sorting_tiebreakers_and_numeric_ordering():
    loc = Location(path="app.py", line_start=10, line_end=10)
    
    # Gaps 7: Numeric sorting (e.g. 20 sorts before 100)
    f_offset_100 = Finding(
        id="p100",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc,
        claim="sql issue",
        metadata={"sub_rule": "sqli", "token_offset": 100}
    )
    
    f_offset_20 = Finding(
        id="p20",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc,
        claim="sql issue",
        metadata={"sub_rule": "sqli", "token_offset": 20}
    )
    
    finalized, _ = finalize_finding_ids([f_offset_100, f_offset_20])
    # 20 must sort before 100 numerically
    assert [f.metadata.get("token_offset") for f in finalized] == [20, 100]
    
    # Test sub_rule alphabetical sort
    f_sub_shell = Finding(
        id="p_shell",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc,
        claim="shell issue",
        metadata={"sub_rule": "shell-true", "token_offset": 50}
    )
    f_sub_sqli = Finding(
        id="p_sqli",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc,
        claim="sql issue",
        metadata={"sub_rule": "sqli", "token_offset": 50}
    )
    finalized, _ = finalize_finding_ids([f_sub_sqli, f_sub_shell])
    assert [f.metadata.get("sub_rule") for f in finalized] == ["shell-true", "sqli"]

    # Test claim SHA tiebreaker
    f_claim_a = Finding(
        id="pc_a",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.MEDIUM,
        location=loc,
        claim="Claim A",  # sha256 starts with 'e'
    )
    f_claim_b = Finding(
        id="pc_b",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.MEDIUM,
        location=loc,
        claim="Claim B",  # sha256 starts with 'a'
    )
    # 'a' < 'e', so pc_b sorts before pc_a
    finalized, _ = finalize_finding_ids([f_claim_a, f_claim_b])
    assert [f.claim for f in finalized] == ["Claim B", "Claim A"]


def test_finalize_non_prose_key_merging_and_metadata_provenance():
    loc1 = Location(path="app.py", line_start=30, line_end=32)
    loc2 = Location(path="app.py", line_start=30, line_end=35)
    
    # Two findings with same anchor AND same non-prose key (sub_rule="sqli", token_offset=100)
    f1 = Finding(
        id="prov1",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.MEDIUM,
        location=loc1,
        claim="First SQL injection claim",
        evidence_ref=["app.py#30"],
        status="contested",
        metadata={"sub_rule": "sqli", "token_offset": 100, "extra_info": "foo"}
    )
    
    f2 = Finding(
        id="prov2",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc2,
        claim="Second SQL injection claim",
        evidence_ref=["app.py#31"],
        status="active",
        metadata={"sub_rule": "sqli", "token_offset": 100, "more_info": "bar"}
    )
    
    finalized, id_map = finalize_finding_ids([f1, f2])
    
    assert len(finalized) == 1
    merged = finalized[0]
    
    # Severity is max (HIGH > MEDIUM)
    assert merged.severity == Severity.HIGH
    # Location line_end is max (35 > 32)
    assert merged.location.line_end == 35
    # Claims are joined
    assert merged.claim == "First SQL injection claim; Second SQL injection claim"
    # Evidence refs are merged
    assert merged.evidence_ref == ["app.py#30", "app.py#31"]
    # Status is active (active > contested)
    assert merged.status == "active"
    # Metadata is merged
    assert merged.metadata["extra_info"] == "foo"
    assert merged.metadata["more_info"] == "bar"
    
    # ID mapping contains both provisional IDs
    assert set(id_map[merged.id]) == {"prov1", "prov2"}
    
    # Preservation of merge provenance directly on the finding object (Gap 6)
    assert set(merged.metadata["merged_from_provisional"]) == {"prov1", "prov2"}


def test_cross_perspective_no_merge():
    loc = Location(path="app.py", line_start=30, line_end=30)
    
    # Same rule and offset, but different perspectives (Gap 2)
    f1 = Finding(
        id="prov_preflight",
        source_agent="preflight_secret_gate",
        perspective="preflight",
        severity=Severity.HIGH,
        location=loc,
        claim="Secret exposed in code",
        metadata={"sub_rule": "secret-exposed", "token_offset": 200}
    )
    
    f2 = Finding(
        id="prov_security",
        source_agent="preflight_secret_gate",
        perspective="security",
        severity=Severity.HIGH,
        location=loc,
        claim="Secret exposed in code",
        metadata={"sub_rule": "secret-exposed", "token_offset": 200}
    )
    
    finalized, _ = finalize_finding_ids([f1, f2])
    
    # They should not be merged due to different perspectives
    assert len(finalized) == 2
    assert {f.perspective for f in finalized} == {"preflight", "security"}
    
    # Verify that attempting to merge them manually throws a ValueError
    with pytest.raises(ValueError, match="Cannot merge findings with different perspectives"):
        from gdg_yorku_submission.finding_ids import merge_finding_objects
        merge_finding_objects([f1, f2])


def test_zero_discriminator_preservation():
    loc = Location(path="app.py", line_start=5, line_end=5)
    
    # token_offset=0 or ast_node_id=0 are truthy/valid discriminators (Gap 3)
    f1 = Finding(
        id="prov1",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc,
        claim="SQL injection in first line",
        metadata={"sub_rule": "sqli", "token_offset": 0}
    )
    
    f2 = Finding(
        id="prov2",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc,
        claim="Another SQL injection in first line",
        metadata={"sub_rule": "sqli", "token_offset": 0}
    )
    
    finalized, id_map = finalize_finding_ids([f1, f2])
    
    # Because token_offset=0 is a valid discriminator, they collapse and are MERGED
    assert len(finalized) == 1
    assert set(id_map[finalized[0].id]) == {"prov1", "prov2"}


def test_llm_ordinals_no_collapse():
    loc = Location(path="app.py", line_start=5, line_end=5)
    
    # Two LLM findings with the exact same claim. (Gap 4)
    # They should NOT merge/collapse. They must get separate ordinals (distinct findings).
    f1 = Finding(
        id="prov1",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.MEDIUM,
        location=loc,
        claim="Divergence X",
    )
    
    f2 = Finding(
        id="prov2",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.MEDIUM,
        location=loc,
        claim="Divergence X",
    )
    
    finalized, id_map = finalize_finding_ids([f1, f2])
    
    # Assertion must expect 2 distinct findings, not 1 (Gap 4)
    assert len(finalized) == 2
    assert finalized[0].id != finalized[1].id
    
    # Each finalized ID should map to exactly 1 provisional ID
    p_ids = [map_val[0] for map_val in id_map.values()]
    assert set(p_ids) == {"prov1", "prov2"}


def test_status_merge_precedence():
    loc = Location(path="app.py", line_start=15, line_end=15)
    
    # Gap 5: verify active > contested > advisory precedence
    def make_finding(fid, status):
        return Finding(
            id=fid,
            source_agent="security_debate",
            perspective="security",
            severity=Severity.HIGH,
            location=loc,
            claim="vulnerability X",
            status=status,
            metadata={"sub_rule": "vuln", "token_offset": 456}
        )
        
    # active + contested -> active
    finalized1, _ = finalize_finding_ids([make_finding("p1", "contested"), make_finding("p2", "active")])
    assert len(finalized1) == 1
    assert finalized1[0].status == "active"
    
    # contested + advisory -> contested
    finalized2, _ = finalize_finding_ids([make_finding("p1", "advisory"), make_finding("p2", "contested")])
    assert len(finalized2) == 1
    assert finalized2[0].status == "contested"
    
    # active + advisory -> active
    finalized3, _ = finalize_finding_ids([make_finding("p1", "advisory"), make_finding("p2", "active")])
    assert len(finalized3) == 1
    assert finalized3[0].status == "active"


def test_heterogeneous_batch_conservation():
    # Gap 1: Property-style test asserting global set conservation
    # We create a mixed batch of findings across various anchors
    loc_a = Location(path="file_a.py", line_start=10, line_end=10)
    loc_b = Location(path="file_b.py", line_start=20, line_end=20)
    
    inputs = [
        # Anchor 1 (file_a.py:10, security_deterministic/security, sub_rule="sqli", offset=10)
        # -> Two detector-backed findings with SAME non-prose offset. They MUST merge.
        Finding(
            id="det1_a",
            source_agent="security_deterministic",
            perspective="security",
            severity=Severity.HIGH,
            location=loc_a,
            claim="SQL injection in user input",
            metadata={"sub_rule": "sqli", "token_offset": 10}
        ),
        Finding(
            id="det1_b",
            source_agent="security_deterministic",
            perspective="security",
            severity=Severity.MEDIUM,
            location=loc_a,
            claim="Unescaped SQL query execution",
            metadata={"sub_rule": "sqli", "token_offset": 10}
        ),
        
        # Anchor 1 (same anchor as above, but offset=20)
        # -> Detector-backed finding on SAME anchor but DIFFERENT non-prose offset. MUST NOT merge.
        Finding(
            id="det2",
            source_agent="security_deterministic",
            perspective="security",
            severity=Severity.HIGH,
            location=loc_a,
            claim="SQL injection in secondary query",
            metadata={"sub_rule": "sqli", "token_offset": 20}
        ),
        
        # Anchor 2 (file_a.py:10, correctness_agent/correctness)
        # -> Two LLM findings with the SAME claim. MUST NOT merge, must receive separate ordinals.
        Finding(
            id="llm1_a",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.MEDIUM,
            location=loc_a,
            claim="Divergent function signature"
        ),
        Finding(
            id="llm1_b",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.MEDIUM,
            location=loc_a,
            claim="Divergent function signature"
        ),
        
        # Anchor 2 (same as above)
        # -> LLM finding on SAME anchor with DIFFERENT claim. MUST NOT merge.
        Finding(
            id="llm2",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.LOW,
            location=loc_a,
            claim="Divergent documentation comments"
        ),
        
        # Anchor 3 (file_b.py:20, correctness_agent/correctness)
        # -> Single finding.
        Finding(
            id="single_b",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.LOW,
            location=loc_b,
            claim="Divergent import statement"
        )
    ]
    
    finalized, id_map = finalize_finding_ids(inputs)
    
    # Expected groups:
    # Anchor 1:
    #   - group (sqli, 10): det1_a + det1_b -> merged into 1 finding
    #   - group (sqli, 20): det2 -> 1 finding
    # Anchor 2:
    #   - llm1_a -> 1 finding
    #   - llm1_b -> 1 finding
    #   - llm2 -> 1 finding
    # Anchor 3:
    #   - single_b -> 1 finding
    # Total finalized findings expected: 1 + 1 + 1 + 1 + 1 + 1 = 6 findings.
    assert len(finalized) == 6
    assert len(id_map) == 6
    
    # Core conservation invariants:
    input_ids = {f.id for f in inputs}
    mapped_input_ids = set()
    for out_id, in_ids in id_map.items():
        # Every output ID maps to a non-empty list of input IDs
        assert len(in_ids) > 0
        for in_id in in_ids:
            # No input ID is duplicated or mapped multiple times
            assert in_id not in mapped_input_ids
            mapped_input_ids.add(in_id)
            
    # All inputs are fully accounted for (union(id_map.values()) == input_ids)
    assert mapped_input_ids == input_ids
    
    # Verify mapping correctness for the merged group
    merged_output_id = None
    for out_id, in_ids in id_map.items():
        if set(in_ids) == {"det1_a", "det1_b"}:
            merged_output_id = out_id
            break
    assert merged_output_id is not None
    
    # Find the finalized finding for that merged output
    merged_finding = next(f for f in finalized if f.id == merged_output_id)
    assert merged_finding.severity == Severity.HIGH
    assert "SQL injection in user input; Unescaped SQL query execution" in merged_finding.claim


def test_parse_discriminator_for_sorting_negative_and_floats():
    # Verify that parse_discriminator_for_sorting sorts negative numbers correctly
    d_neg100 = parse_discriminator_for_sorting("-100")
    d_neg20 = parse_discriminator_for_sorting("-20")
    d_zero = parse_discriminator_for_sorting("0")
    d_pos20 = parse_discriminator_for_sorting("20")
    d_float15 = parse_discriminator_for_sorting("15.5")
    d_str = parse_discriminator_for_sorting("abc")
    d_none = parse_discriminator_for_sorting(None)

    # Expected order: None first, then Numeric (negatives before zero before positive before float), then String last
    assert d_none < d_neg100
    assert d_neg100 < d_neg20
    assert d_neg20 < d_zero
    assert d_zero < d_float15
    assert d_float15 < d_pos20
    assert d_pos20 < d_str


def test_distinct_colocated_findings_with_different_nonprose_keys():
    loc = Location(path="src/app.py", line_start=10, line_end=10)
    
    # f1 and f2 are co-located deterministic findings of the same category,
    # but have DIFFERENT token_offsets (10 vs 20).
    f1 = Finding(
        id="prov1",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc,
        claim="SQL Injection at input validation",
        metadata={"sub_rule": "sqli", "token_offset": 10}
    )
    
    f2 = Finding(
        id="prov2",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.HIGH,
        location=loc,
        claim="SQL Injection at DB execute",
        metadata={"sub_rule": "sqli", "token_offset": 20}
    )
    
    finalized, id_map = finalize_finding_ids([f1, f2])
    
    # They MUST survive as two distinct findings with different stable IDs and unique ordinals
    assert len(finalized) == 2
    assert finalized[0].id != finalized[1].id
    assert finalized[0].metadata.get("token_offset") == 10
    assert finalized[1].metadata.get("token_offset") == 20
    
    # Each provisional ID maps to exactly 1 finalized ID
    p_ids = [map_val[0] for map_val in id_map.values()]
    assert set(p_ids) == {"prov1", "prov2"}


