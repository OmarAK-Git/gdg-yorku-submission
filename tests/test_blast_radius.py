import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from gdg_yorku_submission.app import app
from gdg_yorku_submission.orchestrator import InProcessOrchestrator
from gdg_yorku_submission.schemas import CorpusFile, Location, ReviewFinding
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.blast_radius.orbit_client import OrbitClient, OrbitImpactContext, OrbitPipeline, OrbitMergeRequest, OrbitVulnerability
from gdg_yorku_submission.blast_radius.agent import PythonSymbolExtractor, run_blast_radius_review, make_blast_radius_specialist

def test_orbit_client_is_configured():
    # 1. Unconfigured when env is empty
    with patch.dict(os.environ, {"ORBIT_API_URL": "", "ORBIT_API_TOKEN": "", "USE_FAKE_ORBIT": "false"}):
        client = OrbitClient()
        assert not client.is_configured()

    # 2. Configured in fake mode
    with patch.dict(os.environ, {"ORBIT_API_URL": "", "ORBIT_API_TOKEN": "", "USE_FAKE_ORBIT": "true"}):
        client = OrbitClient()
        assert client.is_configured()

    # 3. Configured with real env variables
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "secret-token", "USE_FAKE_ORBIT": "false"}):
        client = OrbitClient()
        assert client.is_configured()

def test_orbit_client_health_check_fake():
    # 1. Healthy fake check
    client = OrbitClient(use_fake=True)
    assert client.health_check()

    # 2. Unhealthy fake check (using specific unhealthy URL trigger)
    client = OrbitClient(api_url="http://unhealthy", use_fake=True)
    assert not client.health_check()

def test_orbit_client_health_check_real_http():
    # Mocking urlopen
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OrbitClient(api_url="http://orbit.local", api_token="secret", use_fake=False)
        assert client.health_check()

        # Unhealthy HTTP status
        mock_response.status = 500
        assert not client.health_check()

        # Exception raised
        mock_urlopen.side_effect = Exception("Connection refused")
        assert not client.health_check()

def test_orbit_client_query_symbol_fake():
    client = OrbitClient(use_fake=True)
    
    # 1. Symbol that exists in fake db
    res = client.query_symbol("driftstore.db.get_db")
    assert res is not None
    assert res.symbol == "driftstore.db.get_db"
    assert "driftstore-backend" in res.affected_projects
    assert len(res.pipelines) == 1
    assert res.pipelines[0].status == "failed"
    assert len(res.related_vulnerabilities) == 1
    assert res.related_vulnerabilities[0].id == "CVE-2026-9901"

    # 2. Symbol that does not exist
    res = client.query_symbol("nonexistent.func")
    assert res is None

def test_orbit_client_query_symbol_real_http():
    # Mock urllib.request.urlopen to simulate actual HTTP response for the production path
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        # Mock JSON response payload
        mock_payload = {
            "symbol": "requests.get",
            "affected_projects": ["projA"],
            "dependencies": ["depA"],
            "pipelines": [{"id": "pl-1", "status": "success", "web_url": "http://url"}],
            "merge_requests": [{"id": "mr-1", "title": "MR", "state": "opened", "web_url": "http://url"}],
            "related_vulnerabilities": [{"id": "CVE-1", "severity": "medium", "description": "desc"}]
        }
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OrbitClient(api_url="http://orbit.local", api_token="secret-token", use_fake=False)
        impact = client.query_symbol("requests.get")
        
        # Verify urlopen was called with a Request object having correct URL and headers
        mock_urlopen.assert_called_once()
        called_req = mock_urlopen.call_args[0][0]
        assert called_req.full_url == "http://orbit.local/api/v1/blast-radius?symbol=requests.get"
        assert called_req.get_header("Authorization") == "Bearer secret-token"
        assert called_req.get_header("X-orbit-token") == "secret-token"
        assert called_req.get_header("Accept") == "application/json"
        
        # Verify mapped response structure
        assert impact is not None
        assert impact.symbol == "requests.get"
        assert "projA" in impact.affected_projects
        assert "depA" in impact.dependencies
        assert len(impact.pipelines) == 1
        assert impact.pipelines[0].status == "success"
        assert len(impact.related_vulnerabilities) == 1

def test_python_symbol_extractor():
    code = """
import os
import requests
from math import pi, sin as trig_sin
from collections import defaultdict as ddict, Counter

class MyTestClass:
    def __init__(self):
        pass
    
    def my_method(self):
        pass

async def test_async_func():
    pass
"""
    extractor = PythonSymbolExtractor()
    import ast
    tree = ast.parse(code)
    extractor.visit(tree)

    symbols = extractor.symbols
    assert "os" in symbols
    assert "requests" in symbols
    assert "math" in symbols
    assert "math.trig_sin" in symbols
    assert "math.pi" in symbols
    assert "trig_sin" in symbols
    assert "pi" in symbols
    assert "collections" in symbols
    assert "collections.ddict" in symbols
    assert "ddict" in symbols
    assert "MyTestClass" in symbols
    assert "test_async_func" in symbols

def test_agent_unconfigured():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    with patch.dict(os.environ, {"ORBIT_API_URL": "", "ORBIT_API_TOKEN": "", "USE_FAKE_ORBIT": "false"}):
        findings, status, reason = run_blast_radius_review(orch)
        assert findings == []
        assert status == "disabled"
        assert "unconfigured" in reason

def test_agent_unhealthy():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Set config, but mock health check to fail
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://unhealthy", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        findings, status, reason = run_blast_radius_review(orch)
        assert findings == []
        assert status == "unavailable"
        assert "unavailable" in reason

def test_agent_successful_scan():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Setup mock corpus with a python file importing requests
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="import requests\nfrom driftstore.db import get_db\n",
            redacted_text="import requests\nfrom driftstore.db import get_db\n",
            original_line_count=2,
            redacted_to_original_line_map={1: 1, 2: 2},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    # Enable fake orbit client
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        findings, status, reason = run_blast_radius_review(orch)
        assert status == "complete"
        # The fake database contains responses for "requests.get" and "driftstore.db.get_db"
        # Our extractor will find "driftstore.db.get_db" (since get_db is imported from driftstore.db)
        # It will also extract "requests" (which is imported, but not requests.get since requests.get wasn't explicitly imported as from)
        # So we expect "driftstore.db.get_db" to trigger a match
        assert len(findings) >= 1
        
        db_finding = next((f for f in findings if "driftstore.db.get_db" in f.claim), None)
        assert db_finding is not None
        assert db_finding.source_agent == "blast_radius_agent"
        assert db_finding.perspective == "blast_radius"
        # CAPPED AT Severity.MEDIUM (Item 2)
        assert db_finding.severity == Severity.MEDIUM
        assert db_finding.location.path == "src/app.py"
        assert db_finding.location.line_start == 2
        assert db_finding.evidence_ref == ["file:src/app.py#2-2"]
        assert db_finding.status == "active"
        
        # Verify metadata
        metadata = db_finding.metadata
        assert metadata["symbol"] == "driftstore.db.get_db"
        assert metadata["rule_or_category"] == "blast_radius"
        assert "driftstore-backend" in metadata["affected_projects"]
        assert len(metadata["pipelines"]) == 1
        assert metadata["pipelines"][0]["status"] == "failed"

def test_api_integration():
    # Test end-to-end integration via fastapi TestClient
    client = TestClient(app)
    
    import zipfile
    import io
    
    # Build a tiny zip file with a python file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("src/main.py", "from driftstore.db import get_db\n")
        
    zip_data = zip_buffer.getvalue()
    
    # Configure fake orbit client and enable fake LLM to prevent real Vertex calls
    with patch.dict(os.environ, {
        "ORBIT_API_URL": "http://orbit.local",
        "ORBIT_API_TOKEN": "token",
        "USE_FAKE_ORBIT": "true",
        "USE_FAKE_LLM": "true"
    }):
        response = client.post(
            "/review?orchestrator=in_process",
            files={"file": ("repo.zip", zip_data, "application/zip")}
        )
        assert response.status_code == 200
        report = response.json()
        
        # Check that perspective statuses contains blast_radius
        statuses = report["perspective_statuses"]
        blast_status = next((s for s in statuses if s["perspective"] == "blast_radius"), None)
        assert blast_status is not None
        assert blast_status["status"] == "complete"
        
        # Check that the findings include the blast radius finding
        findings = report["findings"]
        blast_findings = [f for f in findings if f["perspective"] == "blast_radius"]
        assert len(blast_findings) == 1
        assert "driftstore.db.get_db" in blast_findings[0]["claim"]

def test_agent_non_identity_line_map():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Setup mock corpus where redacted_text has shifted line numbers.
    # Original text: 5 lines, get_db is on line 5.
    # Redacted text: 2 lines, get_db is on line 2.
    # map_line maps line 2 (redacted) to line 5 (original).
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n\n\n\nfrom driftstore.db import get_db\n",
            redacted_text="\nfrom driftstore.db import get_db\n",
            original_line_count=5,
            redacted_to_original_line_map={1: 1, 2: 5},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        findings, status, reason = run_blast_radius_review(orch)
        assert status == "complete"
        assert len(findings) == 1
        
        f = findings[0]
        # Assert mapped to original line 5
        assert f.location.line_start == 5
        assert f.location.line_end == 5
        assert f.evidence_ref == ["file:src/app.py#5-5"]

def test_agent_out_of_bounds_skipping():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Map maps redacted line 2 to original line 10, but original line count is only 5.
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n\n\n\nfrom driftstore.db import get_db\n",
            redacted_text="\nfrom driftstore.db import get_db\n",
            original_line_count=5,
            redacted_to_original_line_map={1: 1, 2: 10}, # out of bounds!
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        findings, status, reason = run_blast_radius_review(orch)
        assert status == "complete"
        assert len(findings) == 0  # Skipped because of out-of-bounds original coordinate mapping

def test_agent_determinism():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="from driftstore.db import get_db\n",
            redacted_text="from driftstore.db import get_db\n",
            original_line_count=1,
            redacted_to_original_line_map={1: 1},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        findings1, status1, _ = run_blast_radius_review(orch)
        findings2, status2, _ = run_blast_radius_review(orch)
        
        assert status1 == status2
        assert len(findings1) == len(findings2)
        assert findings1[0].id == findings2[0].id
        assert findings1[0].claim == findings2[0].claim
        assert findings1[0].severity == findings2[0].severity

def test_agent_severity_cap():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="from driftstore.db import get_db\n",
            redacted_text="from driftstore.db import get_db\n",
            original_line_count=1,
            redacted_to_original_line_map={1: 1},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    # We patch the client's query_symbol to return a CRITICAL vulnerability context.
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        with patch.object(OrbitClient, "query_symbol") as mock_query:
            mock_query.return_value = OrbitImpactContext(
                symbol="driftstore.db.get_db",
                affected_projects=["proj"],
                dependencies=[],
                pipelines=[],
                merge_requests=[],
                related_vulnerabilities=[
                    OrbitVulnerability(id="CVE-2026-9901", severity="critical", description="exploit")
                ]
            )
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            assert len(findings) == 1
            # Severity MUST be capped at MEDIUM
            assert findings[0].severity == Severity.MEDIUM

def test_dependencies_only_claim_formatting():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="import urllib3\n",
            redacted_text="import urllib3\n",
            original_line_count=1,
            redacted_to_original_line_map={1: 1},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        with patch.object(OrbitClient, "query_symbol") as mock_query:
            mock_query.return_value = OrbitImpactContext(
                symbol="urllib3",
                affected_projects=[],
                dependencies=["some-dep"],
                pipelines=[],
                merge_requests=[],
                related_vulnerabilities=[]
            )
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            assert len(findings) == 1
            claim = findings[0].claim
            assert "depends on" in claim
            assert not claim.endswith(":")

def test_duplicate_symbol_line_deduplication():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="from driftstore.db import get_db\n",
            redacted_text="from driftstore.db import get_db\n",
            original_line_count=1,
            redacted_to_original_line_map={1: 1},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        with patch.object(OrbitClient, "query_symbol") as mock_query:
            mock_query.return_value = OrbitImpactContext(
                symbol="driftstore.db.get_db",
                affected_projects=["proj"],
                dependencies=[],
                pipelines=[],
                merge_requests=[],
                related_vulnerabilities=[]
            )
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            assert len(findings) == 1
            assert findings[0].metadata["symbol"] == "driftstore.db.get_db"

def test_agent_unexpected_query_exception_failsafe():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="from driftstore.db import get_db\n",
            redacted_text="from driftstore.db import get_db\n",
            original_line_count=1,
            redacted_to_original_line_map={1: 1},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        with patch.object(OrbitClient, "query_symbol") as mock_query:
            mock_query.side_effect = RuntimeError("Database timeout")
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            assert len(findings) == 0

def test_blast_coordinator_merge_and_omission():
    f1 = ReviewFinding(
        id="prov-blast-1",
        source_agent="blast_radius_agent",
        perspective="blast_radius",
        severity=Severity.MEDIUM,
        location=Location(path="src/app.py", line_start=10, line_end=10),
        claim="Blast finding 1",
        evidence_ref=["file:src/app.py#10-10"]
    )
    f2 = ReviewFinding(
        id="prov-blast-2",
        source_agent="blast_radius_agent",
        perspective="blast_radius",
        severity=Severity.LOW,
        location=Location(path="src/app.py", line_start=15, line_end=15),
        claim="Blast finding 2",
        evidence_ref=["file:src/app.py#15-15"]
    )
    f3 = ReviewFinding(
        id="prov-blast-3",
        source_agent="blast_radius_agent",
        perspective="blast_radius",
        severity=Severity.INFO,
        location=Location(path="src/app.py", line_start=20, line_end=20),
        claim="Blast finding 3",
        evidence_ref=["file:src/app.py#20-20"]
    )
    
    from gdg_yorku_submission.coordinator.compiler import run_coordinator_compilation
    
    orch = InProcessOrchestrator()
    orch.start_run()
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="\n" * 30,
            redacted_text="\n" * 30,
            original_line_count=30,
            evidence_ref="file:src/app.py"
        )
    }
    orch.set_corpus(corpus)
    
    from gdg_yorku_submission.schemas import PerspectiveStatus, GateStatus
    statuses = [
        PerspectiveStatus(perspective="blast_radius", status="complete", finding_ids=["prov-blast-1", "prov-blast-2", "prov-blast-3"])
    ]
    gate_status = GateStatus(status="complete", finding_ids=[])
    
    orch.write_findings("blast_radius", [f1, f2, f3])
    orch.finalize_ids()
    state = orch.read_state()
    finalized_findings = state["findings"]
    
    id_map = {f.metadata["merged_from_provisional"][0]: f.id for f in finalized_findings}
    
    mock_response = json.dumps({
        "merges": [
            {
                "merged_ids": [id_map["prov-blast-1"], id_map["prov-blast-2"]],
                "consolidated_claim": "Merged blast findings",
                "recommended_next_action": "Remediate merged blast radius dependencies"
            }
        ],
        "omissions": [
            {
                "id": id_map["prov-blast-3"],
                "reason": "INFO severity finding is low value noise"
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
    
    assert len(compiled) == 1
    merged = compiled[0]
    assert merged.perspective == "blast_radius"
    assert merged.source_agent == "blast_radius_agent"
    assert merged.severity == Severity.MEDIUM
    assert sorted(merged.merged_from) == sorted([id_map["prov-blast-1"], id_map["prov-blast-2"]])
    
    assert len(ledger.omitted) == 1
    assert ledger.omitted[0].id == id_map["prov-blast-3"]
    assert "noise" in ledger.omitted[0].reason

def test_agent_symbol_count_cap():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # 25 imports, resulting in 25 unique symbols
    imports_code = "\n".join(f"import lib_{i}" for i in range(25))
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text=imports_code,
            redacted_text=imports_code,
            original_line_count=25,
            redacted_to_original_line_map={i: i for i in range(1, 26)},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        with patch.object(OrbitClient, "query_symbol") as mock_query:
            mock_query.return_value = None
            findings, status, reason = run_blast_radius_review(orch)
            assert status == "complete"
            
            # The count of queried unique symbols should be capped at 20 (Item 3)
            assert mock_query.call_count == 20

def test_agent_wall_clock_budget_termination():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # 5 imports
    imports_code = "import lib_1\nimport lib_2\nimport lib_3\nimport lib_4\nimport lib_5\n"
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text=imports_code,
            redacted_text=imports_code,
            original_line_count=5,
            redacted_to_original_line_map={i: i for i in range(1, 6)},
            evidence_ref="file:src/app.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    orch.set_corpus(corpus)
    
    # Mock time.time() to trigger elapsed time budget threshold
    # First call: start_time = 0.0
    # Second call (first symbol query elapsed check): time.time() = 1.0 (elapsed 1.0s <= 2.0s) -> proceed
    # Third call (second symbol query elapsed check): time.time() = 2.5 (elapsed 2.5s > 2.0s) -> terminate
    time_mock_values = [0.0, 1.0, 2.5, 3.5, 4.5]
    time_index = 0
    def mock_time():
        nonlocal time_index
        val = time_mock_values[min(time_index, len(time_mock_values) - 1)]
        time_index += 1
        return val
        
    with patch.dict(os.environ, {"ORBIT_API_URL": "http://orbit.local", "ORBIT_API_TOKEN": "token", "USE_FAKE_ORBIT": "true"}):
        with patch("time.time", side_effect=mock_time):
            with patch.object(OrbitClient, "query_symbol") as mock_query:
                mock_query.return_value = None
                findings, status, reason = run_blast_radius_review(orch)
                assert status == "complete"
                # Capped by wall-clock query budget termination (Item 3)
                # It should only query 1 symbol before the 2.5s check on the second symbol loop aborts
                assert mock_query.call_count == 1

