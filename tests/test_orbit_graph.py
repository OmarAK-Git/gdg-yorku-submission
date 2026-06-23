"""
Tests for the grounded Orbit graph primitives.

Fixtures are verbatim copies of the live .orbit-captures/ payloads (project
metadata is from a public project; safe to commit). Tests are pinned to the
REAL captured request/response so the builders cannot drift from what Orbit
actually accepts/returns.
"""
import json
from unittest.mock import patch, MagicMock

import pytest

from gdg_yorku_submission.blast_radius.orbit_graph import (
    parse_orbit_response,
    single_node_query,
    project_scoped_traversal,
    execute_query,
    OrbitQueryResult,
    OrbitQueryError,
)

# Verbatim error/empty envelopes captured from the live POST /api/v4/orbit/query
CAPTURED_EMPTY_RESULT = {
    "result": {"format_version": "2.1.0", "query_type": "traversal", "nodes": [], "edges": []},
    "query_type": "traversal",
    "row_count": 0,
}
CAPTURED_COMPILE_ERROR = {
    "code": "compile_error",
    "message": "schema violation: traversal and aggregation queries require node_ids or filters on at least one node to avoid full edge table scans",
}

# Verbatim from .orbit-captures/project-result.json
CAPTURED_PROJECT_RESULT = {
    "result": {
        "format_version": "2.1.0",
        "query_type": "traversal",
        "nodes": [
            {
                "type": "Project",
                "id": "83658494",
                "star_count": 0,
                "updated_at": "2026-06-23T01:41:54Z",
                "visibility_level": "public",
                "traversal_path": "1/135557159/135557474/",
                "description": "",
                "name": "gdg-yorku-submission",
                "last_activity_at": "2026-06-23T01:41:41Z",
                "created_at": "2026-06-23T01:41:41Z",
                "full_path": "fish763926/gdg-yorku-submission",
                "archived": "false",
            }
        ],
        "edges": [],
    },
    "query_type": "traversal",
    "row_count": 1,
}

# Verbatim from .orbit-captures/project-query.json
CAPTURED_PROJECT_QUERY = {
    "query": {
        "query_type": "traversal",
        "node": {
            "id": "p",
            "entity": "Project",
            "columns": "*",
            "filters": {"full_path": {"op": "eq", "value": "fish763926/gdg-yorku-submission"}},
        },
        "limit": 5,
    },
    "response_format": "raw",
}


def test_parse_real_project_result():
    res = parse_orbit_response(CAPTURED_PROJECT_RESULT)
    assert isinstance(res, OrbitQueryResult)
    assert res.query_type == "traversal"
    assert res.format_version == "2.1.0"
    assert res.row_count == 1
    assert res.edges == []
    assert len(res.nodes) == 1

    node = res.nodes[0]
    # type/id are lifted out of the column bag...
    assert node.type == "Project"
    assert node.id == "83658494"
    # ...and the remaining columns are preserved verbatim in properties.
    assert node.get("full_path") == "fish763926/gdg-yorku-submission"
    assert node.get("name") == "gdg-yorku-submission"
    assert node.get("visibility_level") == "public"
    assert "type" not in node.properties and "id" not in node.properties


def test_parse_is_lenient_on_empty_and_garbage():
    # Graceful degradation: absent/empty/garbage -> empty result, never raises.
    assert parse_orbit_response({}).nodes == []
    assert parse_orbit_response({"result": {}}).nodes == []
    assert parse_orbit_response({"result": {"nodes": ["bad", 5, None]}}).nodes == []
    assert parse_orbit_response(None).nodes == []  # type: ignore[arg-type]


def test_nodes_of_type_filter():
    res = parse_orbit_response(CAPTURED_PROJECT_RESULT)
    assert len(res.nodes_of_type("Project")) == 1
    assert res.nodes_of_type("Vulnerability") == []


def test_single_node_query_reproduces_capture():
    # The builder must reproduce the exact payload Orbit accepted.
    built = single_node_query(
        "Project",
        "p",
        columns="*",
        filters={"full_path": {"op": "eq", "value": "fish763926/gdg-yorku-submission"}},
        limit=5,
    )
    assert built == CAPTURED_PROJECT_QUERY


def test_project_scoped_traversal_shape():
    # Mirrors the vulns/pipelines/merge-requests capture payloads.
    built = project_scoped_traversal(
        "Vulnerability", "v", "fish763926/gdg-yorku-submission", limit=50
    )
    q = built["query"]
    assert built["response_format"] == "raw"
    assert q["query_type"] == "traversal"
    assert q["limit"] == 50
    assert q["nodes"][0] == {"id": "v", "entity": "Vulnerability", "columns": "*"}
    assert q["nodes"][1]["entity"] == "Project"
    assert q["nodes"][1]["filters"]["full_path"]["value"] == "fish763926/gdg-yorku-submission"
    rel = q["relationships"][0]
    assert rel == {"type": "IN_PROJECT", "from": "v", "to": "p", "direction": "outgoing"}


def _mock_urlopen_returning(payload: dict):
    """Returns a patch target that makes urlopen yield `payload` as JSON bytes."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = resp
    return cm


def test_execute_query_posts_correct_request_and_parses():
    payload = single_node_query(
        "Project", "p", filters={"full_path": {"op": "eq", "value": "x/y"}}, limit=5
    )
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _mock_urlopen_returning(CAPTURED_PROJECT_RESULT)
        res = execute_query("https://gitlab.com/api/v4/orbit/", "glpat-tok", payload)

        req = mock_urlopen.call_args[0][0]
        # endpoint + auth + method are exactly what the live capture confirmed
        assert req.full_url == "https://gitlab.com/api/v4/orbit/query"
        assert req.get_method() == "POST"
        assert req.get_header("Authorization") == "Bearer glpat-tok"
        assert req.get_header("Content-type") == "application/json"
        # body is the DSL, UTF-8, and crucially has NO BOM (the bug we hit)
        assert not req.data.startswith(b"\xef\xbb\xbf")
        assert json.loads(req.data.decode("utf-8")) == payload
        # parsed result
        assert res.row_count == 1
        assert res.nodes[0].type == "Project"


def test_execute_query_empty_result_degrades_to_zero_rows():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _mock_urlopen_returning(CAPTURED_EMPTY_RESULT)
        res = execute_query("https://gitlab.com/api/v4/orbit", "t", {"query": {}})
        assert res.row_count == 0
        assert res.nodes == []


def test_execute_query_error_envelope_raises_orbit_error():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _mock_urlopen_returning(CAPTURED_COMPILE_ERROR)
        with pytest.raises(OrbitQueryError) as ei:
            execute_query("https://gitlab.com/api/v4/orbit", "t", {"query": {}})
        assert "node_ids or filters" in str(ei.value)


# Trimmed verbatim from the live .orbit-captures/imported-symbols.json (source code IS indexed).
CAPTURED_IMPORTS_RESULT = {
    "result": {
        "format_version": "2.1.0",
        "query_type": "traversal",
        "nodes": [
            {"type": "File", "id": "8772629577363248613", "path": "src/gdg_yorku_submission/app.py"},
            {
                "type": "ImportedSymbol",
                "id": "1083009831980034273",
                "identifier_name": "File",
                "import_path": "fastapi",
                "import_type": "FromImport",
                "file_path": "src/gdg_yorku_submission/app.py",
                "start_line": "5",
                "end_line": "5",
            },
        ],
        "edges": [
            {"from": "Branch", "from_id": "2854479161200117190", "to": "Project", "to_id": "83658494", "type": "IN_PROJECT"},
            {"from": "File", "from_id": "8772629577363248613", "to": "ImportedSymbol", "to_id": "1083009831980034273", "type": "IMPORTS"},
        ],
    },
    "query_type": "traversal",
    "row_count": 30,
}


def test_parse_imports_edges_and_symbol_properties():
    res = parse_orbit_response(CAPTURED_IMPORTS_RESULT)
    # ImportedSymbol properties land in the bag with the real field names we mapped.
    sym = res.nodes_of_type("ImportedSymbol")[0]
    assert sym.get("identifier_name") == "File"
    assert sym.get("import_path") == "fastapi"
    assert sym.get("file_path") == "src/gdg_yorku_submission/app.py"

    # Edges parse into the confirmed {from,from_id,to,to_id,type} shape.
    imports = res.edges_of_type("IMPORTS")
    assert len(imports) == 1
    e = imports[0]
    assert e.from_type == "File" and e.from_id == "8772629577363248613"
    assert e.to_type == "ImportedSymbol" and e.to_id == "1083009831980034273"
    # IN_PROJECT anchor edge is also present and typed.
    assert res.edges_of_type("IN_PROJECT")[0].to_type == "Project"
