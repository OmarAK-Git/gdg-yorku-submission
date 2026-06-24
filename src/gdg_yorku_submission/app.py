import io
import json
import os
import zipfile

import anyio

# Load .env before any code reads env vars (credentials, model config, orbit, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from typing import Any, AsyncIterator, Dict, List, Tuple
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, StreamingResponse
from gdg_yorku_submission.schemas import (
    ReviewReport,
    ReviewFinding,
    Location,
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

current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Ordered pipeline stages surfaced to streaming clients. The index/total pair lets
# the UI drive a real progress bar without hard-coding percentages.
PIPELINE_TOTAL_STEPS = 6


@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")


@app.get("/ui")
async def redirect_to_ui():
    return RedirectResponse(url="/static/index.html")


async def _run_pipeline_events(
    content: bytes,
) -> AsyncIterator[Tuple[str, Dict[str, Any]]]:
    """
    Shared review pipeline, expressed as an async generator that yields one
    ``(event_name, payload)`` tuple per stage.

    Both ``POST /review`` (blocking) and ``POST /review/stream`` (SSE) consume this
    single generator so their behavior can never drift. Stages are emitted in order:
    ``ingestion`` -> ``secret_gate`` -> ``correctness`` -> ``security`` ->
    ``blast_radius`` -> ``compile``, each as a ``("step", ...)`` event transitioning
    ``running`` -> ``complete``. The terminal event is either:

      * ``("report", {"report": ReviewReport})`` on success, or
      * ``("error", {"step", "message", "http_status"})`` on a stage that cannot
        proceed (ingestion or compilation).

    Redaction invariant: payloads only ever carry safe metadata — stage names, human
    labels, counts, the already-built ``corpus_summary``, and the fully compiled
    (already-redacted) ``ReviewReport``. Raw file contents and specialist reasoning
    text are never streamed.

    The temporary extraction directory is owned by this generator's ``with`` block, so
    it stays alive for the full duration of iteration (including while the terminal
    report event is consumed).
    """
    import tempfile
    from gdg_yorku_submission.ingestion import HardenedZipExtractor, IngestionError
    from gdg_yorku_submission.corpus import build_corpus
    from gdg_yorku_submission.preflight.secrets import run_secret_scan
    from gdg_yorku_submission.security import make_security_specialist
    from gdg_yorku_submission.correctness.agent import make_correctness_specialist
    from gdg_yorku_submission.blast_radius import make_blast_radius_specialist

    total = PIPELINE_TOTAL_STEPS

    with tempfile.TemporaryDirectory() as temp_dir_path:
        # --- Stage 1: Ingestion (verify + harden + extract) ---
        yield ("step", {
            "step": "ingestion", "status": "running",
            "label": "Extracting & hardening archive", "index": 1, "total": total,
        })
        try:
            manifest = HardenedZipExtractor.extract(content, temp_dir_path)
            corpus_summary = {
                "file_count": manifest.total_extracted_count,
                "total_bytes": manifest.total_extracted_bytes,
                "skipped_files": len(manifest.skipped_files),
                "skipped_log": {
                    k: {"skipped_reason": v.skipped_reason}
                    for k, v in manifest.skipped_files.items()
                }
            }
        except IngestionError as e:
            yield ("error", {
                "step": "ingestion",
                "message": f"Ingestion failed: {str(e)}",
                "http_status": 400,
            })
            return
        yield ("step", {
            "step": "ingestion", "status": "complete",
            "label": "Archive extracted", "index": 1, "total": total,
            "corpus_summary": corpus_summary,
        })

        # Always use the ADK orchestrator (falls back to in-process internally if ADK
        # is unavailable), matching the blocking endpoint's behavior.
        orch = AdkOrchestrator()
        orch.start_run()
        redaction_ctx = orch.get_redaction_context()
        corpus = build_corpus(temp_dir_path, manifest)

        # --- Stage 2: Pre-flight secret gate (run-scoped redaction context) ---
        yield ("step", {
            "step": "secret_gate", "status": "running",
            "label": "Pre-flight secret scan", "index": 2, "total": total,
        })
        gate_findings = run_secret_scan(corpus, redaction_ctx)
        orch.set_corpus(corpus)
        orch.set_corpus_summary(corpus_summary)
        orch.run_secret_gate(gate_findings)
        yield ("step", {
            "step": "secret_gate", "status": "complete",
            "label": "Secret scan complete", "index": 2, "total": total,
            "secret_count": len(gate_findings),
        })

        # --- Stage 3: Correctness specialist ---
        yield ("step", {
            "step": "correctness", "status": "running",
            "label": "Correctness specialist", "index": 3, "total": total,
        })
        orch.run_specialist("correctness", make_correctness_specialist(orch))
        yield ("step", {
            "step": "correctness", "status": "complete",
            "label": "Correctness specialist complete", "index": 3, "total": total,
        })

        # --- Stage 4: Security specialist (AST baseline + optional debate) ---
        # The debate loop can run for several minutes (multiple sequential LLM
        # turns); we intentionally do NOT time-box it. Instead we run the specialist
        # concurrently and relay its live, redaction-safe progress events (debate
        # rounds/scores) to the client as ("debate", payload) events while it works,
        # so the user can watch real progress rather than wait blind.
        yield ("step", {
            "step": "security", "status": "running",
            "label": "Security specialist (AST baseline + debate)", "index": 4, "total": total,
        })
        send_stream, receive_stream = anyio.create_memory_object_stream(256)

        def _debate_sink(payload: Dict[str, Any]) -> None:
            try:
                send_stream.send_nowait(payload)
            except Exception:
                # Buffer full or closed: drop the cosmetic progress event rather
                # than apply backpressure to the debate.
                pass

        orch.set_event_sink(_debate_sink)
        try:
            async with anyio.create_task_group() as tg:
                async def _run_security():
                    try:
                        await orch.run_specialist_async(
                            "security", make_security_specialist(orch)
                        )
                    finally:
                        send_stream.close()  # signals end-of-stream to the relay below

                tg.start_soon(_run_security)
                async for payload in receive_stream:
                    yield ("debate", payload)
        finally:
            orch.set_event_sink(None)
            send_stream.close()
            receive_stream.close()

        yield ("step", {
            "step": "security", "status": "complete",
            "label": "Security specialist complete", "index": 4, "total": total,
        })

        # --- Stage 5: Blast-radius specialist ---
        yield ("step", {
            "step": "blast_radius", "status": "running",
            "label": "Blast-radius specialist", "index": 5, "total": total,
        })
        orch.run_specialist("blast_radius", make_blast_radius_specialist(orch))
        yield ("step", {
            "step": "blast_radius", "status": "complete",
            "label": "Blast-radius specialist complete", "index": 5, "total": total,
        })

        # --- Stage 6: Compile final report ---
        yield ("step", {
            "step": "compile", "status": "running",
            "label": "Compiling final report", "index": 6, "total": total,
        })
        try:
            report = orch.compile_report()
        except Exception as e:
            yield ("error", {
                "step": "compile",
                "message": f"Failed to compile report: {str(e)}",
                "http_status": 500,
            })
            return
        yield ("step", {
            "step": "compile", "status": "complete",
            "label": "Report compiled", "index": 6, "total": total,
        })

        # Terminal success event carries the fully compiled (already-redacted) report.
        yield ("report", {"report": report})


@app.post("/review", response_model=ReviewReport)
async def review_upload(
    file: UploadFile = File(...),
):
    """
    Accepts a .zip archive upload, verifies its format integrity,
    runs correctness and security checks using the selected orchestrator,
    and returns a fully-accounted ReviewReport.

    This is the blocking variant: it drives the shared pipeline generator to the
    terminal event and returns the compiled report (or raises the matching HTTP
    error). See ``POST /review/stream`` for the live, step-by-step variant.
    """
    content = await file.read()

    async for event_name, payload in _run_pipeline_events(content):
        if event_name == "error":
            raise HTTPException(
                status_code=payload.get("http_status", 500),
                detail=payload["message"],
            )
        if event_name == "report":
            return payload["report"]

    # The generator always terminates in a report or error event; reaching here
    # means the pipeline produced nothing, which is an internal failure.
    raise HTTPException(status_code=500, detail="Review pipeline produced no report.")


def _format_sse(event: str, data: Dict[str, Any]) -> str:
    """Serialize a single Server-Sent Event frame (one ``event:``/``data:`` block)."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _sse_frames(content: bytes) -> AsyncIterator[str]:
    """
    Adapt the shared pipeline generator into a text/event-stream byte stream.

    Every stage event is forwarded as an SSE frame. The terminal ``report`` event is
    serialized from the compiled ReviewReport (identical content to what
    ``POST /review`` returns for the same input). Any unexpected exception is converted
    into a terminal ``error`` frame so the stream always closes cleanly rather than
    tearing the connection (never-fails guarantee).
    """
    try:
        async for event_name, payload in _run_pipeline_events(content):
            if event_name == "report":
                report = payload["report"]
                yield _format_sse("report", report.model_dump(mode="json"))
            elif event_name == "error":
                # http_status is an internal hint for the blocking endpoint; drop it
                # from the wire payload but keep the redaction-safe message + step.
                yield _format_sse("error", {
                    "step": payload.get("step", "unknown"),
                    "message": payload.get("message", "Review pipeline failed."),
                })
            else:
                yield _format_sse(event_name, payload)
    except Exception as e:  # never tear the stream; surface a clean terminal error frame
        yield _format_sse("error", {
            "step": "unknown",
            "message": f"Review pipeline aborted: {type(e).__name__}",
        })


@app.post("/review/stream")
async def review_stream(
    file: UploadFile = File(...),
):
    """
    Streaming variant of ``POST /review``.

    Accepts the same multipart upload, but instead of blocking until the report is
    ready, it returns a ``text/event-stream`` that emits a Server-Sent Event after each
    pipeline stage (ingestion, secret gate, correctness, security, blast-radius,
    compile) and a terminal ``report`` (or ``error``) event.
    """
    content = await file.read()
    return StreamingResponse(
        _sse_frames(content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Disable proxy buffering (e.g. nginx) so frames flush as they are produced.
            "X-Accel-Buffering": "no",
        },
    )
