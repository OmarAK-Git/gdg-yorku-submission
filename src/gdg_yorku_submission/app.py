import io
import zipfile
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from gdg_yorku_submission.schemas import (
    ReviewReport,
    ReviewFinding,
    Location
)
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.orchestrator import (
    InProcessOrchestrator,
    AdkOrchestrator
)

app = FastAPI(
    title="GDG-YorkU Code Review Tool API",
    version="0.1.0"
)


def correctness_specialist_stub() -> List[ReviewFinding]:
    """Stub correctness specialist returning a standard finding."""
    return [
        ReviewFinding(
            id="stub-correctness-finding",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.HIGH,
            location=Location(path="src/app.py", line_start=1, line_end=5),
            claim="Stub correctness finding claim",
            evidence_ref=["file:src/app.py#1-5"],
            status="active",
            metadata={"rule_or_category": "correctness_rule"}
        )
    ]


def security_specialist_stub() -> List[ReviewFinding]:
    """Stub security specialist returning a standard finding."""
    return [
        ReviewFinding(
            id="stub-security-finding",
            source_agent="security_deterministic",
            perspective="security",
            severity=Severity.CRITICAL,
            location=Location(path="src/main.py", line_start=10, line_end=10),
            claim="Stub security finding claim",
            evidence_ref=["file:src/main.py#10"],
            status="active",
            metadata={"rule_or_category": "security_rule"}
        )
    ]


@app.get("/")
def read_root():
    return {"status": "running", "app": "GDG-YorkU Code Review Tool"}


@app.post("/review", response_model=ReviewReport)
async def review_upload(
    file: UploadFile = File(...),
    orchestrator: str = Query("adk", pattern="^(adk|in_process)$")
):
    """
    Accepts a .zip archive upload, verifies its format integrity,
    runs correctness and security checks using the selected orchestrator,
    and returns a fully-accounted ReviewReport.
    """
    import tempfile
    import zipfile
    from gdg_yorku_submission.ingestion import HardenedZipExtractor, IngestionError

    content = await file.read()

    with tempfile.TemporaryDirectory() as temp_dir_path:
        # 1. Ingestion: verify and extract
        try:
            manifest = HardenedZipExtractor.extract(content, temp_dir_path)
            
            corpus_summary = {
                "file_count": manifest.total_extracted_count,
                "total_bytes": manifest.total_extracted_bytes,
                "skipped_files": len(manifest.skipped_files)
            }
        except IngestionError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Ingestion failed: {str(e)}"
            )

        # 2. Select orchestrator
        if orchestrator == "in_process":
            orch = InProcessOrchestrator()
        else:
            orch = AdkOrchestrator()

        # 3. Start run
        orch.start_run()
        orch.set_corpus_summary(corpus_summary)

        # 4. Run specialists
        orch.run_specialist("correctness", correctness_specialist_stub)
        orch.run_specialist("security", security_specialist_stub)

        # 5. Compile and return report
        try:
            report = orch.compile_report()
            return report
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to compile report: {str(e)}"
            )
