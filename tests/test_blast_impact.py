"""
Tests for blast-radius computation over the Orbit code graph.

Fixtures are trimmed-but-real rows/edges from .orbit-captures/definitions.json
and calls.json (the redaction.py call chain: sanitize_value -> redact, and
sanitize_value -> RedactionContext).
"""
from gdg_yorku_submission.blast_radius.orbit_graph import parse_orbit_response
from gdg_yorku_submission.blast_radius.impact import build_impact_graph, summarize_blast

SANITIZE = "3534170436609274784"   # sanitize_value (Function)
REDACT = "4810010306816112823"     # RedactionContext.redact (Method)
CTX = "2345585782495468229"        # RedactionContext (Class)

_DEF = lambda _id, name, fqn, line, dtype: {
    "type": "Definition", "id": _id, "name": name, "fqn": fqn,
    "file_path": "src/gdg_yorku_submission/preflight/redaction.py",
    "start_line": str(line), "end_line": str(line + 1), "definition_type": dtype,
}

DEFINITIONS = parse_orbit_response({
    "result": {"format_version": "2.1.0", "query_type": "traversal", "nodes": [
        _DEF(SANITIZE, "sanitize_value", "src...redaction.sanitize_value", 123, "Function"),
        _DEF(REDACT, "redact", "src...redaction.RedactionContext.redact", 60, "Method"),
        _DEF(CTX, "RedactionContext", "src...redaction.RedactionContext", 5, "Class"),
    ], "edges": []},
    "query_type": "traversal", "row_count": 3,
})

CALLS = parse_orbit_response({
    "result": {"format_version": "2.1.0", "query_type": "traversal", "nodes": [], "edges": [
        # real shape: caller -> callee
        {"from": "Definition", "from_id": SANITIZE, "to": "Definition", "to_id": REDACT, "type": "CALLS"},
        {"from": "Definition", "from_id": SANITIZE, "to": "Definition", "to_id": CTX, "type": "CALLS"},
        {"from": "Definition", "from_id": SANITIZE, "to": "Definition", "to_id": SANITIZE, "type": "CALLS"},  # self-recursion
    ]},
    "query_type": "traversal", "row_count": 3,
})


def test_build_graph_adjacency():
    g = build_impact_graph(DEFINITIONS, CALLS)
    # forward: sanitize_value calls redact and RedactionContext (self-call dropped)
    assert g.callees[SANITIZE] == {REDACT, CTX}
    assert SANITIZE not in g.callees.get(SANITIZE, set())
    # reverse: redact is called-by sanitize_value
    assert g.callers[REDACT] == {SANITIZE}


def test_dependents_is_the_blast_radius():
    g = build_impact_graph(DEFINITIONS, CALLS)
    # changing redact() blasts back to sanitize_value
    assert g.dependents(REDACT) == {SANITIZE}
    # sanitize_value has no callers here -> empty blast
    assert g.dependents(SANITIZE) == set()


def test_summarize_blast_orders_and_filters():
    g = build_impact_graph(DEFINITIONS, CALLS)
    summaries = summarize_blast(g, min_dependents=1)
    # redact and RedactionContext each have 1 dependent (sanitize_value); sanitize_value has 0 -> excluded
    ids = {s.definition.id for s in summaries}
    assert ids == {REDACT, CTX}
    for s in summaries:
        assert SANITIZE in s.dependent_ids
        assert "redaction.py" in next(iter(s.dependent_files))
