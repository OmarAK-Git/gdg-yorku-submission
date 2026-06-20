import io
import zipfile
from fastapi.testclient import TestClient
from gdg_yorku_submission.app import app

client = TestClient(app)


def create_tiny_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hello.py", "print('Hello, world!')")
        z.writestr("/etc/passwd", "root:x:0:0:")  # Skipped due to absolute path
    return buf.getvalue()


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_review_upload_happy_path_adk():
    zip_bytes = create_tiny_zip()
    files = {"file": ("test.zip", zip_bytes, "application/zip")}
    
    response = client.post("/review", files=files, params={"orchestrator": "adk"})
    assert response.status_code == 200
    
    report = response.json()
    assert "run_metadata" in report
    assert report["run_metadata"]["orchestrator_type"] == "AdkOrchestrator"
    assert len(report["findings"]) == 1
    
    # Check correctness perspective
    statuses = {ps["perspective"]: ps for ps in report["perspective_statuses"]}
    assert "correctness" in statuses
    assert statuses["correctness"]["status"] == "complete"
    assert report["corpus_summary"]["file_count"] == 1
    assert report["corpus_summary"]["total_bytes"] > 0
    assert report["corpus_summary"]["skipped_files"] == 1
    assert "security" in statuses
    assert statuses["security"]["status"] == "complete"

    # Verify ID finalization happened and IDs are hashes
    for f in report["findings"]:
        assert len(f["id"]) == 64  # SHA-256 hex string


def test_review_upload_happy_path_in_process():
    zip_bytes = create_tiny_zip()
    files = {"file": ("test.zip", zip_bytes, "application/zip")}
    
    response = client.post("/review", files=files, params={"orchestrator": "in_process"})
    assert response.status_code == 200
    
    report = response.json()
    assert report["run_metadata"]["orchestrator_type"] == "InProcessOrchestrator"
    assert len(report["findings"]) == 1


def test_review_upload_invalid_zip():
    bad_bytes = b"not a zip file content"
    files = {"file": ("test.txt", bad_bytes, "text/plain")}
    
    response = client.post("/review", files=files)
    assert response.status_code == 400
    assert "Ingestion failed" in response.json()["detail"]


def test_review_upload_specialist_failure(monkeypatch):
    def failing_stub():
        raise RuntimeError("Correctness agent failed.")
    monkeypatch.setattr("gdg_yorku_submission.app.correctness_specialist_stub", failing_stub)

    zip_bytes = create_tiny_zip()
    files = {"file": ("test.zip", zip_bytes, "application/zip")}
    
    response = client.post(
        "/review",
        files=files,
        params={"orchestrator": "in_process"}
    )
    assert response.status_code == 200
    
    report = response.json()
    statuses = {ps["perspective"]: ps for ps in report["perspective_statuses"]}
    
    # Correctness specialist failed but security succeeded, run completed
    assert statuses["correctness"]["status"] == "failed"
    assert "Correctness agent failed" in statuses["correctness"]["reason"]
    assert statuses["security"]["status"] == "complete"
    
    # Only security finding should be active/present in report findings
    assert len(report["findings"]) == 0


def test_review_upload_with_secrets():
    # Zip file with a synthetic API key, a dotenv secret, and a .gitignore
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(".gitignore", "config/.env\n")
        z.writestr("src/config.py", "GOOGLE_API_KEY = 'AIzaSyAbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'\nprint('hello')\n")
        z.writestr("config/.env", "AWS_SECRET = 'abcdefjhjklmnopqrstwxyz0123456789012345A'\n")
    zip_bytes = buf.getvalue()
    
    files = {"file": ("test.zip", zip_bytes, "application/zip")}
    response = client.post("/review", files=files, params={"orchestrator": "in_process"})
    assert response.status_code == 200
    
    report = response.json()
    
    # 1. Assert raw secrets never leak in the response JSON
    report_str = response.text
    assert "AIzaSyAbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" not in report_str
    assert "abcdefjhjklmnopqrstwxyz0123456789012345A" not in report_str
    
    # 2. Check that the prompt-exposed secret is promoted to ReviewFinding
    # report.findings should contain the stub security finding, stub correctness, and promoted secret finding
    perspectives = [f["perspective"] for f in report["findings"]]
    assert perspectives.count("security") == 1 # promoted secret only
    
    # Check secret scan summary contains both secrets
    assert len(report["secret_scan_summary"]) == 2
    secret_types = [gf["secret_type"] for gf in report["secret_scan_summary"]]
    assert "Google API Key" in secret_types
    assert "AWS Secret Access Key" in secret_types
    
    # Ignored secret in config/.env should have Severity.INFO, and NOT be promoted
    info_secrets = [gf for gf in report["secret_scan_summary"] if gf["severity"] == "info"]
    assert len(info_secrets) == 1
    assert info_secrets[0]["secret_type"] == "AWS Secret Access Key"
    
    # The active/promoted finding is for Google API Key
    # Google API Key is prompt_exposed, so it should be promoted to active findings.
    active_promoted = [f for f in report["findings"] if f["source_agent"] == "preflight_secret_gate"]
    assert len(active_promoted) == 1
    assert active_promoted[0]["severity"] == "high" # Google API Key matches non-critical credential -> high
    assert active_promoted[0]["metadata"]["secret_type"] == "Google API Key"
    
    # Verify accounting ledger has both included active findings + stub correctness (total 2 findings)
    assert len(report["accounting_ledger"]["included"]) == 2

