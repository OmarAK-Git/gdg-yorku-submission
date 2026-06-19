import io
import zipfile
from fastapi.testclient import TestClient
from gdg_yorku_submission.app import app

client = TestClient(app)


def create_tiny_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hello.py", "print('Hello, world!')")
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
    assert len(report["findings"]) == 2
    
    # Check correctness perspective
    statuses = {ps["perspective"]: ps for ps in report["perspective_statuses"]}
    assert "correctness" in statuses
    assert statuses["correctness"]["status"] == "complete"
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
    assert len(report["findings"]) == 2


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
    assert len(report["findings"]) == 1
    assert report["findings"][0]["perspective"] == "security"
