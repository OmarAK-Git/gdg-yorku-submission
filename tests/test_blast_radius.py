import os
import json
import pytest
import hashlib
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from gdg_yorku_submission.app import app
from gdg_yorku_submission.orchestrator import InProcessOrchestrator
from gdg_yorku_submission.schemas import CorpusFile, Location, ReviewFinding
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.blast_radius.orbit_client import OrbitClient
from gdg_yorku_submission.blast_radius.orbit_graph import OrbitQueryResult, OrbitNode, OrbitEdge
from gdg_yorku_submission.blast_radius.agent import run_blast_radius_review, make_blast_radius_specialist

# Verbatim response sample parsed helper
from gdg_yorku_submission.blast_radius.orbit_graph import parse_orbit_response

MOCK_DEFS = parse_orbit_response({
    "result": {
        "format_version": "2.1.0",
        "query_type": "traversal",
        "nodes": [
            {"type": "Definition", "id": "1", "name": "func1", "fqn": "src.app.func1", "file_path": "src/app.py", "start_line": "10", "end_line": "12", "definition_type": "Function"},
            {"type": "Definition", "id": "2", "name": "func2", "fqn": "src.app.func2", "file_path": "src/app.py", "start_line": "20", "end_line": "22", "definition_type": "Function"},
            {"type": "Definition", "id": "3", "name": "func3", "fqn": "src.app.func3", "file_path": "src/app.py", "start_line": "30", "end_line": "32", "definition_type": "Function"}
        ],
        "edges": []
    },
    "query_type": "traversal",
    "row_count": 3
})

MOCK_CALLS = parse_orbit_response({
    "result": {
        "format_version": "2.1.0",
        "query_type": "traversal",
        "nodes": [],
        "edges": [
            {"from": "Definition", "from_id": "1", "to": "Definition", "to_id": "2", "type": "CALLS"},
            {"from": "Definition", "from_id": "2", "to": "Definition", "to_id": "3", "type": "CALLS"}
        ]
    },
    "query_type": "traversal",
    "row_count": 2
})

MOCK_IMPORTS = parse_orbit_response({
    "result": {
        "format_version": "2.1.0",
        "query_type": "traversal",
        "nodes": [
            {"type": "ImportedSymbol", "id": "i1", "identifier_name": "FastAPI", "import_path": "fastapi", "file_path": "src/app.py", "start_line": "2"}
        ],
        "edges": []
    },
    "query_type": "traversal",
    "row_count": 1
})


def test_orbit_client_is_configured():
    # 1. Unconfigured when env is empty
    with patch.dict(os.environ, {"ORBIT_API_URL": "", "ORBIT_API_TOKEN": "", "ORBIT_PROJECT_PATH": "", "USE_FAKE_ORBIT": "false"}):
        client = OrbitClient()
        assert not client.is_configured()

    # 2. Configured in fake mode
    with patch.dict(os.environ, {"ORBIT_API_URL": "", "ORBIT_API_TOKEN": "", "ORBIT_PROJECT_PATH": "", "USE_FAKE_ORBIT": "true"}):
        client = OrbitClient()
        assert client.is_configured()

    # 3. Configured with real env variables
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "secret-token", "ORBIT_PROJECT_PATH": "my-project", "USE_FAKE_ORBIT": "false"}):
        client = OrbitClient()
        assert client.is_configured()


def _mock_urlopen_returning(payload: dict):
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = resp
    return cm


def test_client_transport_post():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _mock_urlopen_returning({
            "result": {
                "format_version": "2.1.0",
                "query_type": "traversal",
                "nodes": [{"type": "Project", "id": "123", "full_path": "x/y"}],
                "edges": []
            },
            "row_count": 1
        })
        client = OrbitClient(
            api_url="https://gitlab.com/api/v4/orbit",
            api_token="my-token",
            project_path="x/y",
            use_fake=False
        )
        
        assert client.health_check()
        
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://gitlab.com/api/v4/orbit/query"
        assert req.get_method() == "POST"
        assert req.get_header("Authorization") == "Bearer my-token"
        assert req.get_header("Content-type") == "application/json"
        
        assert not req.data.startswith(b"\xef\xbb\xbf")
        parsed_body = json.loads(req.data.decode("utf-8"))
        assert parsed_body["query"]["node"]["entity"] == "Project"


def test_client_transport_fetch_definitions_and_parse():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _mock_urlopen_returning({
            "result": {
                "format_version": "2.1.0",
                "query_type": "traversal",
                "nodes": [
                    {"type": "Definition", "id": "4583269700307719499", "name": "test_dummy", "fqn": "samples.test_dummy", "file_path": "src/app.py", "start_line": "10", "end_line": "12", "definition_type": "Function"}
                ],
                "edges": []
            },
            "query_type": "traversal",
            "row_count": 1
        })
        client = OrbitClient(
            api_url="https://gitlab.com/api/v4/orbit",
            api_token="my-token",
            project_path="fish763926/gdg-yorku-submission",
            use_fake=False
        )
        res = client.fetch_definitions()
        
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://gitlab.com/api/v4/orbit/query"
        
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["query"]["query_type"] == "traversal"
        nodes = payload["query"]["nodes"]
        assert nodes[0]["entity"] == "Definition"
        assert nodes[3]["filters"]["full_path"]["value"] == "fish763926/gdg-yorku-submission"
        
        assert res.row_count == 1
        assert len(res.nodes_of_type("Definition")) == 1
        defn = res.nodes_of_type("Definition")[0]
        assert defn.get("name") == "test_dummy"
        assert defn.get("fqn") == "samples.test_dummy"


def test_client_transport_fetch_calls_and_parse():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _mock_urlopen_returning({
            "result": {
                "format_version": "2.1.0",
                "query_type": "traversal",
                "nodes": [
                    {"type": "Definition", "id": "1", "name": "src_func", "fqn": "src.app.src_func", "file_path": "src/app.py", "start_line": "10", "end_line": "12", "definition_type": "Function"},
                    {"type": "Definition", "id": "2", "name": "dst_func", "fqn": "src.app.dst_func", "file_path": "src/app.py", "start_line": "20", "end_line": "22", "definition_type": "Function"}
                ],
                "edges": [
                    {"from": "Definition", "from_id": "1", "to": "Definition", "to_id": "2", "type": "CALLS"}
                ]
            },
            "query_type": "traversal",
            "row_count": 1
        })
        client = OrbitClient(
            api_url="https://gitlab.com/api/v4/orbit",
            api_token="my-token",
            project_path="fish763926/gdg-yorku-submission",
            use_fake=False
        )
        res = client.fetch_calls()
        
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://gitlab.com/api/v4/orbit/query"
        
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["query"]["query_type"] == "traversal"
        nodes = payload["query"]["nodes"]
        
        # Verify that both src and dst nodes are Definition and contain file_path, start_line, end_line
        src_node = next((n for n in nodes if n["id"] == "src"), None)
        dst_node = next((n for n in nodes if n["id"] == "dst"), None)
        assert src_node is not None
        assert dst_node is not None
        
        assert src_node["entity"] == "Definition"
        assert dst_node["entity"] == "Definition"
        
        for n in (src_node, dst_node):
            cols = n["columns"]
            assert "file_path" in cols
            assert "start_line" in cols
            assert "end_line" in cols
            assert "fqn" in cols
            assert "definition_type" in cols


def test_agent_happy_path_scan():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="from fastapi import FastAPI\n" * 50,
            redacted_text="from fastapi import FastAPI\n" * 50,
            original_line_count=50,
            redacted_to_original_line_map={i: i for i in range(1, 51)},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success",
            redaction_applied=True
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "fish763926/gdg-yorku-submission",
        "USE_FAKE_ORBIT": "true"
    }):
        with patch.object(OrbitClient, "fetch_definitions", return_value=MOCK_DEFS), \
             patch.object(OrbitClient, "fetch_calls", return_value=MOCK_CALLS), \
             patch.object(OrbitClient, "fetch_imports", return_value=MOCK_IMPORTS), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            assert len(findings) == 2  # Definition 3 (2 deps) and Definition 2 (1 dep)
            
            assert findings[0].metadata["symbol"] == "src.app.func3"
            assert findings[1].metadata["symbol"] == "src.app.func2"
            
            f = findings[0]
            assert f.location.path == "src/app.py"
            assert f.location.line_start == 30
            assert f.location.line_end == 32
            assert f.evidence_ref == ["file:src/app.py#30-32"]
            assert "fastapi" in f.claim
            assert "src.app.func3" in f.claim
            assert "2 definitions" in f.claim


def test_severity_cap():
    orch = InProcessOrchestrator()
    orch.start_run()
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n" * 50,
            redacted_text="\n" * 50,
            original_line_count=50,
            redacted_to_original_line_map={i: i for i in range(1, 51)},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success",
            redaction_applied=True
        )
    }
    orch.set_corpus(corpus)
    
    # 1. Test case: naturally HIGH severity (>= 10 dependents) capped to MEDIUM
    nodes_10 = [
        {"type": "Definition", "id": "target", "name": "target", "fqn": "src.app.target", "file_path": "src/app.py", "start_line": "10", "end_line": "12", "definition_type": "Function"}
    ]
    for i in range(10):
        nodes_10.append({"type": "Definition", "id": f"dep{i}", "name": f"dep{i}", "fqn": f"src.app.dep{i}", "file_path": "src/app.py", "start_line": "15", "end_line": "16", "definition_type": "Function"})
        
    edges_10 = []
    for i in range(10):
        edges_10.append({"from": "Definition", "from_id": f"dep{i}", "to": "Definition", "to_id": "target", "type": "CALLS"})
        
    large_defs = parse_orbit_response({"result": {"nodes": nodes_10, "edges": []}, "row_count": len(nodes_10)})
    large_calls = parse_orbit_response({"result": {"nodes": [], "edges": edges_10}, "row_count": len(edges_10)})
    
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "true"
    }):
        with patch.object(OrbitClient, "fetch_definitions", return_value=large_defs), \
             patch.object(OrbitClient, "fetch_calls", return_value=large_calls), \
             patch.object(OrbitClient, "fetch_imports", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            target_finding = next((f for f in findings if f.metadata["symbol"] == "src.app.target"), None)
            assert target_finding is not None
            assert target_finding.severity == Severity.MEDIUM

    # 2. Test case: naturally CRITICAL severity (from critical vulnerability) capped to MEDIUM
    mock_vulns = parse_orbit_response({
        "result": {
            "format_version": "2.1.0",
            "query_type": "traversal",
            "nodes": [
                {"type": "Vulnerability", "id": "v1", "severity": "critical", "description": "SQL injection"}
            ],
            "edges": []
        },
        "query_type": "traversal",
        "row_count": 1
    })

    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "true"
    }):
        with patch.object(OrbitClient, "fetch_definitions", return_value=MOCK_DEFS), \
             patch.object(OrbitClient, "fetch_calls", return_value=MOCK_CALLS), \
             patch.object(OrbitClient, "fetch_imports", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=mock_vulns), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            # Both emitted findings (which normally have LOW severity) upgraded directly to MEDIUM due to project vulnerability
            assert len(findings) == 2
            assert all(f.severity == Severity.MEDIUM for f in findings)


def test_client_non_overlapping_fixtures_uses_calls_coords():
    orch = InProcessOrchestrator()
    orch.start_run()
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n" * 50,
            redacted_text="\n" * 50,
            original_line_count=50,
            redacted_to_original_line_map={i: i for i in range(1, 51)},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success",
            redaction_applied=True
        )
    }
    orch.set_corpus(corpus)

    # 1. definitions result only has node "1" (the caller)
    defs_result = parse_orbit_response({
        "result": {
            "format_version": "2.1.0",
            "query_type": "traversal",
            "nodes": [
                {"type": "Definition", "id": "1", "name": "caller_func", "fqn": "src.app.caller_func", "file_path": "src/app.py", "start_line": "10", "end_line": "12", "definition_type": "Function"}
            ],
            "edges": []
        },
        "query_type": "traversal",
        "row_count": 1
    })

    # 2. calls result has CALLS edge from "1" to "2", and node "2" (the target/callee)
    # complete with coordinates which will be fetched because calls is self-sufficient!
    calls_result = parse_orbit_response({
        "result": {
            "format_version": "2.1.0",
            "query_type": "traversal",
            "nodes": [
                {"type": "Definition", "id": "2", "name": "target_func", "fqn": "src.app.target_func", "file_path": "src/app.py", "start_line": "20", "end_line": "22", "definition_type": "Function"}
            ],
            "edges": [
                {"from": "Definition", "from_id": "1", "to": "Definition", "to_id": "2", "type": "CALLS"}
            ]
        },
        "query_type": "traversal",
        "row_count": 1
    })

    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "true"
    }):
        with patch.object(OrbitClient, "fetch_definitions", return_value=defs_result), \
             patch.object(OrbitClient, "fetch_calls", return_value=calls_result), \
             patch.object(OrbitClient, "fetch_imports", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            
            # Since changing target_func (node 2) calls caller_func (node 1 is caller/dependent),
            # changing target_func has 1 dependent (node 1).
            # We assert target_func finding exists and has coordinates from calls result (20 to 22).
            target_finding = next((f for f in findings if f.metadata["symbol"] == "src.app.target_func"), None)
            assert target_finding is not None
            assert target_finding.location.line_start == 20
            assert target_finding.location.line_end == 22
            assert target_finding.location.path == "src/app.py"


def test_agent_non_identity_line_map_uses_orbit_coords():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Non-identity line map shifts line coordinates
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n" * 250,
            redacted_text="\n" * 50,
            original_line_count=250,
            redacted_to_original_line_map={30: 200, 32: 202},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success",
            redaction_applied=True
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "true"
    }):
        with patch.object(OrbitClient, "fetch_definitions", return_value=MOCK_DEFS), \
             patch.object(OrbitClient, "fetch_calls", return_value=MOCK_CALLS), \
             patch.object(OrbitClient, "fetch_imports", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            
            # Check coordinates are original Orbit coordinates 30-32 (verbatim, not double-mapped to 200-202)
            f = next(f for f in findings if f.metadata["symbol"] == "src.app.func3")
            assert f.location.line_start == 30
            assert f.location.line_end == 32
            assert f.evidence_ref == ["file:src/app.py#30-32"]


def test_coordinate_skip():
    orch = InProcessOrchestrator()
    orch.start_run()
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n" * 5,
            redacted_text="\n" * 5,
            original_line_count=5, # only 5 lines!
            redacted_to_original_line_map={i: i for i in range(1, 6)},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success",
            redaction_applied=True
        )
    }
    orch.set_corpus(corpus)
    
    # 0: parent definition (valid, caller)
    # 1: start_line > original_line_count (10 > 5)
    # 2: file path not in corpus (src/other.py) - missing file path
    # 3: start_line < 1 (0) - out of bounds start
    # 4: start_line > end_line (3 > 2) - inverted lines
    # 5: end_line > original_line_count (2 to 10) - out of bounds end
    nodes = [
        {"type": "Definition", "id": "0", "name": "parent", "fqn": "src.app.parent", "file_path": "src/app.py", "start_line": "1", "end_line": "2", "definition_type": "Function"},
        {"type": "Definition", "id": "1", "name": "out_of_bounds_start", "fqn": "src.app.out_of_bounds_start", "file_path": "src/app.py", "start_line": "10", "end_line": "12", "definition_type": "Function"},
        {"type": "Definition", "id": "2", "name": "missing_file", "fqn": "src.other.missing_file", "file_path": "src/other.py", "start_line": "1", "end_line": "2", "definition_type": "Function"},
        {"type": "Definition", "id": "3", "name": "out_of_bounds_zero", "fqn": "src.app.out_of_bounds_zero", "file_path": "src/app.py", "start_line": "0", "end_line": "2", "definition_type": "Function"},
        {"type": "Definition", "id": "4", "name": "inverted", "fqn": "src.app.inverted", "file_path": "src/app.py", "start_line": "3", "end_line": "2", "definition_type": "Function"},
        {"type": "Definition", "id": "5", "name": "out_of_bounds_end", "fqn": "src.app.out_of_bounds_end", "file_path": "src/app.py", "start_line": "2", "end_line": "10", "definition_type": "Function"}
    ]
    edges = [
        {"from": "Definition", "from_id": "0", "to": "Definition", "to_id": "1", "type": "CALLS"},
        {"from": "Definition", "from_id": "0", "to": "Definition", "to_id": "2", "type": "CALLS"},
        {"from": "Definition", "from_id": "0", "to": "Definition", "to_id": "3", "type": "CALLS"},
        {"from": "Definition", "from_id": "0", "to": "Definition", "to_id": "4", "type": "CALLS"},
        {"from": "Definition", "from_id": "0", "to": "Definition", "to_id": "5", "type": "CALLS"}
    ]
    
    bad_defs = parse_orbit_response({"result": {"nodes": nodes, "edges": []}, "row_count": len(nodes)})
    bad_calls = parse_orbit_response({"result": {"nodes": [], "edges": edges}, "row_count": len(edges)})
    
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "true"
    }):
        with patch.object(OrbitClient, "fetch_definitions", return_value=bad_defs), \
             patch.object(OrbitClient, "fetch_calls", return_value=bad_calls), \
             patch.object(OrbitClient, "fetch_imports", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            # All bad coordinate targets and missing files are skipped.
            # "parent" itself has 0 dependents, so it does not produce a summary finding.
            assert len(findings) == 0


def test_failsafe_handling():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # 1. Unconfigured project path
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "ORBIT_PROJECT_PATH": "", "USE_FAKE_ORBIT": "false"}):
        findings, status, reason = run_blast_radius_review(orch)
        assert status == "disabled"
        assert len(findings) == 0


def test_failsafe_health_check_failed_unreachable():
    orch = InProcessOrchestrator()
    orch.start_run()
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "false" # force real check
    }):
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "unavailable"
            assert len(findings) == 0


def test_failsafe_auxiliary_fetch_exception():
    orch = InProcessOrchestrator()
    orch.start_run()
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n" * 50,
            redacted_text="\n" * 50,
            original_line_count=50,
            redacted_to_original_line_map={i: i for i in range(1, 51)},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success",
            redaction_applied=True
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "true"
    }):
        # Definitions and Calls succeed, but imports query throws exception
        with patch.object(OrbitClient, "fetch_definitions", return_value=MOCK_DEFS), \
             patch.object(OrbitClient, "fetch_calls", return_value=MOCK_CALLS), \
             patch.object(OrbitClient, "fetch_imports", side_effect=RuntimeError("API Failure")), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            # Should complete successfully, degrading imports enrichment to empty
            assert len(findings) == 2
            assert all("File imports:" not in f.claim for f in findings)


def test_compiler_conservation_and_omission():
    f1 = ReviewFinding(
        id="prov-blast-1",
        source_agent="blast_radius_agent",
        perspective="blast_radius",
        severity=Severity.MEDIUM,
        location=Location(path="src/app.py", line_start=10, line_end=12),
        claim="Claim 1",
        evidence_ref=["file:src/app.py#10-12"]
    )
    # Finding 2 is LOW severity (below floor) -> coordinator compilation should omit it
    f2 = ReviewFinding(
        id="prov-blast-2",
        source_agent="blast_radius_agent",
        perspective="blast_radius",
        severity=Severity.LOW,
        location=Location(path="src/app.py", line_start=20, line_end=22),
        claim="Claim 2",
        evidence_ref=["file:src/app.py#20-22"]
    )
    
    from gdg_yorku_submission.coordinator.compiler import run_coordinator_compilation
    
    orch = InProcessOrchestrator()
    orch.start_run()
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n" * 50,
            redacted_text="\n" * 50,
            original_line_count=50,
            evidence_ref="file:src/app.py"
        )
    }
    orch.set_corpus(corpus)
    
    from gdg_yorku_submission.schemas import PerspectiveStatus, GateStatus
    statuses = [
        PerspectiveStatus(perspective="blast_radius", status="complete", finding_ids=["prov-blast-1", "prov-blast-2"])
    ]
    gate_status = GateStatus(status="complete", finding_ids=[])
    
    orch.write_findings("blast_radius", [f1, f2])
    orch.finalize_ids()
    state = orch.read_state()
    finalized_findings = state["findings"]
    
    id_map = {f.metadata["merged_from_provisional"][0]: f.id for f in finalized_findings}
    
    # Coordinator mock JSON response: omit prov-blast-2
    mock_response = json.dumps({
        "merges": [],
        "omissions": [
            {
                "id": id_map["prov-blast-2"],
                "reason": "LOW severity finding below high threshold floor"
            }
        ],
        "recommended_actions": {}
    })
    
    from gdg_yorku_submission.llm.gemini import GeminiClient
    fake_client = GeminiClient(use_fake=True, fake_responses=[mock_response])
    
    compiled, contested, ledger = run_coordinator_compilation(
        orch,
        finalized_findings,
        statuses,
        gate_status,
        gemini_client=fake_client
    )
    
    # f1 compiles to output report verbatim
    assert len(compiled) == 1
    assert compiled[0].id == id_map["prov-blast-1"]
    
    # f2 is omitted, ledger records omission
    assert len(ledger.omitted) == 1
    assert ledger.omitted[0].id == id_map["prov-blast-2"]
    assert "floor" in ledger.omitted[0].reason


def test_agent_determinism_shuffled_input():
    orch = InProcessOrchestrator()
    orch.start_run()
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n" * 50,
            redacted_text="\n" * 50,
            original_line_count=50,
            redacted_to_original_line_map={i: i for i in range(1, 51)},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success",
            redaction_applied=True
        )
    }
    orch.set_corpus(corpus)
    
    # Shuffled nodes and edges
    import random
    
    nodes1 = list(MOCK_DEFS.nodes)
    nodes2 = list(MOCK_DEFS.nodes)
    random.shuffle(nodes2)
    
    edges1 = list(MOCK_CALLS.edges)
    edges2 = list(MOCK_CALLS.edges)
    random.shuffle(edges2)
    
    defs1 = OrbitQueryResult(nodes=nodes1, edges=MOCK_DEFS.edges, query_type="traversal", row_count=len(nodes1))
    defs2 = OrbitQueryResult(nodes=nodes2, edges=MOCK_DEFS.edges, query_type="traversal", row_count=len(nodes2))
    
    calls1 = OrbitQueryResult(nodes=MOCK_CALLS.nodes, edges=edges1, query_type="traversal", row_count=len(edges1))
    calls2 = OrbitQueryResult(nodes=MOCK_CALLS.nodes, edges=edges2, query_type="traversal", row_count=len(edges2))
    
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "true"
    }):
        # First run
        with patch.object(OrbitClient, "fetch_definitions", return_value=defs1), \
             patch.object(OrbitClient, "fetch_calls", return_value=calls1), \
             patch.object(OrbitClient, "fetch_imports", return_value=MOCK_IMPORTS), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            findings1, status1, _ = run_blast_radius_review(orch)
            
        # Second run (with shuffled node/edge arrays)
        with patch.object(OrbitClient, "fetch_definitions", return_value=defs2), \
             patch.object(OrbitClient, "fetch_calls", return_value=calls2), \
             patch.object(OrbitClient, "fetch_imports", return_value=MOCK_IMPORTS), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            findings2, status2, _ = run_blast_radius_review(orch)
            
        assert status1 == status2
        assert len(findings1) == len(findings2)
        for f1, f2 in zip(findings1, findings2):
            assert f1.id == f2.id
            assert f1.claim == f2.claim
            assert f1.severity == f2.severity
            assert f1.location.line_start == f2.location.line_start
            assert f1.location.line_end == f2.location.line_end
            assert f1.evidence_ref == f2.evidence_ref


def test_orbit_metadata_redaction():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Register a secret in the run-specific redaction context
    redaction_ctx = orch.get_redaction_context()
    redaction_ctx.register_secret("my_super_secret_token_abc123", "API_KEY")
    
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="from fastapi import FastAPI\n" * 50,
            redacted_text="from fastapi import FastAPI\n" * 50,
            original_line_count=50,
            redacted_to_original_line_map={i: i for i in range(1, 51)},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success",
            redaction_applied=True
        )
    }
    orch.set_corpus(corpus)
    
    # Construct mock definitions containing the secret in FQN
    secret_defs = parse_orbit_response({
        "result": {
            "format_version": "2.1.0",
            "query_type": "traversal",
            "nodes": [
                {"type": "Definition", "id": "1", "name": "my_super_secret_token_abc123", "fqn": "src.app.my_super_secret_token_abc123", "file_path": "src/app.py", "start_line": "10", "end_line": "12", "definition_type": "Function"},
                {"type": "Definition", "id": "2", "name": "func2", "fqn": "src.app.func2", "file_path": "src/app.py", "start_line": "20", "end_line": "22", "definition_type": "Function"}
            ],
            "edges": []
        },
        "query_type": "traversal",
        "row_count": 2
    })
    
    secret_calls = parse_orbit_response({
        "result": {
            "format_version": "2.1.0",
            "query_type": "traversal",
            "nodes": [],
            "edges": [
                {"from": "Definition", "from_id": "2", "to": "Definition", "to_id": "1", "type": "CALLS"}
            ]
        },
        "query_type": "traversal",
        "row_count": 1
    })
    
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "true"
    }):
        with patch.object(OrbitClient, "fetch_definitions", return_value=secret_defs), \
             patch.object(OrbitClient, "fetch_calls", return_value=secret_calls), \
             patch.object(OrbitClient, "fetch_imports", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            assert len(findings) == 1
            f = findings[0]
            
            # The secret must be replaced by its redacted placeholder in the claim and metadata FQN
            assert "my_super_secret_token_abc123" not in f.claim
            assert "my_super_secret_token_abc123" not in f.metadata["symbol"]
            assert "REDACTED_API_KEY" in f.claim
            assert "REDACTED_API_KEY" in f.metadata["symbol"]


def test_api_e2e_integration():
    client = TestClient(app)
    
    import zipfile
    import io
    
    # Build tiny zip containing src/app.py
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("src/app.py", "\n" * 50)
        
    zip_data = zip_buffer.getvalue()
    
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "ORBIT_PROJECT_PATH": "x/y",
        "USE_FAKE_ORBIT": "true",
        "USE_FAKE_LLM": "true"
    }):
        with patch.object(OrbitClient, "fetch_definitions", return_value=MOCK_DEFS), \
             patch.object(OrbitClient, "fetch_calls", return_value=MOCK_CALLS), \
             patch.object(OrbitClient, "fetch_imports", return_value=MOCK_IMPORTS), \
             patch.object(OrbitClient, "fetch_vulnerabilities", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_pipelines", return_value=OrbitQueryResult()), \
             patch.object(OrbitClient, "fetch_merge_requests", return_value=OrbitQueryResult()):
            
            response = client.post(
                "/review?orchestrator=in_process",
                files={"file": ("repo.zip", zip_data, "application/zip")}
            )
            assert response.status_code == 200
            report = response.json()
            
            statuses = report["perspective_statuses"]
            blast_status = next((s for s in statuses if s["perspective"] == "blast_radius"), None)
            assert blast_status is not None
            assert blast_status["status"] == "complete"
            
            findings = report["findings"]
            blast_findings = [f for f in findings if f["perspective"] == "blast_radius"]
            
            omitted = report["accounting_ledger"]["omitted"]
            blast_omitted = [o for o in omitted if o["id"].startswith("prov-blast")]
            assert len(blast_omitted) + len(blast_findings) == 2
