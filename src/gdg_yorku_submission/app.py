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

        # 2. Select orchestrator and start run
        if orchestrator == "in_process":
            orch = InProcessOrchestrator()
        else:
            orch = AdkOrchestrator()

        orch.start_run()
        redaction_ctx = orch.get_redaction_context()

        # Ingestion: build corpus and run pre-flight secret scan with run-specific context
        from gdg_yorku_submission.corpus import build_corpus
        from gdg_yorku_submission.preflight.secrets import run_secret_scan
        
        corpus = build_corpus(temp_dir_path, manifest)
        gate_findings = run_secret_scan(corpus, redaction_ctx)

        # Persist redacted corpus and metadata in shared state
        orch.set_corpus(corpus)
        orch.set_corpus_summary(corpus_summary)
        orch.run_secret_gate(gate_findings)

        # 4. Run specialists
        from gdg_yorku_submission.security import make_security_specialist
        from gdg_yorku_submission.correctness.agent import make_correctness_specialist
        orch.run_specialist("correctness", make_correctness_specialist(orch))
        orch.run_specialist("security", make_security_specialist(orch))

        # 5. Compile and return report
        try:
            report = orch.compile_report()
            return report
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to compile report: {str(e)}"
            )
