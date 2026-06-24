"""
Tests for the SSE streaming endpoint ``POST /review/stream`` (Task 25).

Covers:
  * Stage event ordering (ingestion -> ... -> compile -> report).
  * Parity: the terminal report event matches what blocking ``POST /review`` returns.
  * Redaction invariant: raw secrets never appear anywhere in the streamed body.
  * Terminal ``error`` events on compile failure and ingestion failure (never-fails:
    the stream closes cleanly with an error frame instead of tearing the connection).
"""
import io
import json
import zipfile

from fastapi.testclient import TestClient

from gdg_yorku_submission.app import app

client = TestClient(app)


# Expected ordered (step, status) pairs for a successful run.
EXPECTED_STEP_SEQUENCE = [
    ("ingestion", "running"),
    ("ingestion", "complete"),
    ("secret_gate", "running"),
    ("secret_gate", "complete"),
    ("correctness", "running"),
    ("correctness", "complete"),
    ("security", "running"),
    ("security", "complete"),
    ("blast_radius", "running"),
    ("blast_radius", "complete"),
    ("compile", "running"),
    ("compile", "complete"),
]


def create_tiny_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "SPEC.md",
            "This is SPEC content.\nRequirement 1 is documented here.\n"
            + "\n".join(f"Line {i}." for i in range(3, 16)),
        )
        z.writestr(
            "src/app.py",
            "def my_func():\n    pass\n" + "".join(f"# line {i}\n" for i in range(3, 13)),
        )
        z.writestr("hello.py", "print('Hello, world!')")
    return buf.getvalue()


def create_secret_zip() -> bytes:
    """Zip carrying a planted Google API key + a gitignored secret."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "SPEC.md",
            "This is SPEC content.\n" + "\n".join(f"Line {i}." for i in range(2, 16)),
        )
        z.writestr(".gitignore", "config/.env\n")
        z.writestr(
            "src/config.py",
            "GOOGLE_API_KEY = 'AIzaSyAbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'\nprint('hello')\n",
        )
        z.writestr(
            "config/.env",
            "AWS_SECRET = 'abcdefjhjklmnopqrstwxyz0123456789012345A'\n",
        )
    return buf.getvalue()


def parse_sse(body: str):
    """Parse a raw SSE body into an ordered list of (event_name, data_dict)."""
    events = []
    for block in body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_name = "message"
        data_lines = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())
        if not data_lines:
            continue
        events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def post_stream(zip_bytes: bytes):
    files = {"file": ("test.zip", zip_bytes, "application/zip")}
    response = client.post("/review/stream", files=files)
    return response


# --------------------------------------------------------------------------- #
# AC-25-01: event ordering
# --------------------------------------------------------------------------- #
def test_stream_emits_stages_in_order():
    response = post_stream(create_tiny_zip())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse(response.text)

    step_pairs = [
        (data["step"], data["status"])
        for name, data in events
        if name == "step"
    ]
    assert step_pairs == EXPECTED_STEP_SEQUENCE

    # The stream terminates in exactly one report event, after all steps.
    assert events[-1][0] == "report"
    assert sum(1 for name, _ in events if name == "report") == 1
    assert not any(name == "error" for name, _ in events)

    # Each step event carries index/total progress metadata.
    for name, data in events:
        if name == "step":
            assert data["total"] == 6
            assert 1 <= data["index"] <= 6


# --------------------------------------------------------------------------- #
# AC-25-02: report parity with the blocking endpoint
# --------------------------------------------------------------------------- #
def _strip_volatile(report: dict) -> dict:
    """Drop run-specific metadata that legitimately differs between two runs."""
    report = json.loads(json.dumps(report))  # deep copy
    meta = report.get("run_metadata", {})
    for key in ("start_time", "duration_ms", "run_id"):
        meta.pop(key, None)
    return report


def test_stream_report_matches_blocking():
    zip_bytes = create_tiny_zip()

    files = {"file": ("test.zip", zip_bytes, "application/zip")}
    blocking = client.post("/review", files=files)
    assert blocking.status_code == 200
    blocking_report = blocking.json()

    stream_events = parse_sse(post_stream(zip_bytes).text)
    report_events = [data for name, data in stream_events if name == "report"]
    assert len(report_events) == 1
    streamed_report = report_events[0]

    # Stable run_metadata fields must match exactly...
    assert (
        streamed_report["run_metadata"]["orchestrator_type"]
        == blocking_report["run_metadata"]["orchestrator_type"]
    )
    assert (
        streamed_report["run_metadata"]["compilation_mode"]
        == blocking_report["run_metadata"]["compilation_mode"]
    )

    # ...and everything except run-specific volatile metadata must deep-equal.
    assert _strip_volatile(streamed_report) == _strip_volatile(blocking_report)


# --------------------------------------------------------------------------- #
# AC-25-03: redaction invariant across the whole stream
# --------------------------------------------------------------------------- #
def test_stream_never_leaks_raw_secrets():
    response = post_stream(create_secret_zip())
    assert response.status_code == 200

    body = response.text
    # Raw secret values must appear in NO frame of the stream.
    assert "AIzaSyAbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" not in body
    assert "abcdefjhjklmnopqrstwxyz0123456789012345A" not in body

    # But the run still completes and the secret scan summary is present (redacted).
    events = parse_sse(body)
    report = [data for name, data in events if name == "report"][0]
    assert len(report["secret_scan_summary"]) == 2


# --------------------------------------------------------------------------- #
# AC-25-04: terminal error event on compile failure (never-fails: clean close)
# --------------------------------------------------------------------------- #
def test_stream_compile_failure_emits_error_event(monkeypatch):
    def boom(self, *args, **kwargs):
        raise RuntimeError("synthetic compile failure")

    monkeypatch.setattr(
        "gdg_yorku_submission.orchestrator.AdkOrchestrator.compile_report",
        boom,
    )

    response = post_stream(create_tiny_zip())
    # Stream itself is a clean HTTP 200; the failure is an in-band error frame.
    assert response.status_code == 200

    events = parse_sse(response.text)
    names = [name for name, _ in events]

    # No report event; exactly one terminal error event for the compile stage.
    assert "report" not in names
    error_events = [data for name, data in events if name == "error"]
    assert len(error_events) == 1
    assert error_events[0]["step"] == "compile"
    assert "synthetic compile failure" in error_events[0]["message"]
    # The internal http_status hint must not leak onto the wire payload.
    assert "http_status" not in error_events[0]

    # The compile stage at least started before failing.
    assert ("compile", "running") in [
        (d["step"], d["status"]) for n, d in events if n == "step"
    ]


# --------------------------------------------------------------------------- #
# Ingestion failure also terminates the stream with a clean error frame.
# --------------------------------------------------------------------------- #
def test_stream_ingestion_failure_emits_error_event():
    files = {"file": ("bad.txt", b"this is not a zip", "text/plain")}
    response = client.post("/review/stream", files=files)
    assert response.status_code == 200

    events = parse_sse(response.text)
    names = [name for name, _ in events]
    assert "report" not in names

    error_events = [data for name, data in events if name == "error"]
    assert len(error_events) == 1
    assert error_events[0]["step"] == "ingestion"
    assert "Ingestion failed" in error_events[0]["message"]
