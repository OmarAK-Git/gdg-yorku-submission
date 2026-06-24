"""
Capture live Orbit responses to JSON files for use as offline mock fixtures.

Runs the same six blast-radius queries as orbit_smoke.py against the real Orbit
API (credentials from .env), but instead of just printing counts it saves the
*raw* response envelope of each query to scripts/orbit_capture/<name>.json.

These raw envelopes are exactly what the client parses, so they can be replayed
as fixtures (USE_FAKE_ORBIT) without touching the network.

Usage (PowerShell):
    python scripts/orbit_capture.py

Output:
    scripts/orbit_capture/definitions.json
    scripts/orbit_capture/calls.json
    scripts/orbit_capture/imports.json
    scripts/orbit_capture/vulnerabilities.json
    scripts/orbit_capture/pipelines.json
    scripts/orbit_capture/merge_requests.json
    scripts/orbit_capture/_manifest.json   (project_path + row counts, no secrets)

The token is NEVER written to any output file. Zip the orbit_capture/ folder
(or just the files) and hand it over.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT_DIR = ROOT / "scripts" / "orbit_capture"


def load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, ignores blanks/#comments. No deps."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def main() -> int:
    load_dotenv(ROOT / ".env")

    from gdg_yorku_submission.blast_radius import orbit_graph
    from gdg_yorku_submission.blast_radius.orbit_client import OrbitClient

    client = OrbitClient()
    print(f"api_url       = {client.api_url}")
    print(f"project_path  = {client.project_path}")
    print(f"token set     = {bool(client.api_token)}")
    print(f"timeout       = {client.timeout}s")

    if not client.is_configured():
        print("\nNOT CONFIGURED. Fill ORBIT_API_URL / ORBIT_API_TOKEN / ORBIT_PROJECT_PATH in .env")
        return 2

    # Wrap _interpret so we grab the raw envelope each query received, in order.
    captured_raw: list = []
    original_interpret = orbit_graph._interpret

    def _capturing_interpret(raw):
        captured_raw.append(raw)
        return original_interpret(raw)

    orbit_graph._interpret = _capturing_interpret

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fetchers = [
        ("definitions", client.fetch_definitions),
        ("calls", client.fetch_calls),
        ("imports", client.fetch_imports),
        ("vulnerabilities", client.fetch_vulnerabilities),
        ("pipelines", client.fetch_pipelines),
        ("merge_requests", client.fetch_merge_requests),
    ]

    manifest = {"project_path": client.project_path, "queries": {}}
    try:
        for name, fn in fetchers:
            captured_raw.clear()
            try:
                res = fn()
            except Exception as e:  # noqa: BLE001 - surface any live failure
                print(f"  {name:16s} ERROR: {type(e).__name__}: {e}")
                manifest["queries"][name] = {"error": f"{type(e).__name__}: {e}"}
                continue

            # The fetch makes exactly one query -> one captured raw envelope.
            raw = captured_raw[-1] if captured_raw else None
            (OUT_DIR / f"{name}.json").write_text(
                json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            manifest["queries"][name] = {
                "row_count": res.row_count,
                "nodes": len(res.nodes),
                "edges": len(res.edges),
            }
            print(f"  {name:16s} row_count={res.row_count} nodes={len(res.nodes)} edges={len(res.edges)} -> {name}.json")
    finally:
        orbit_graph._interpret = original_interpret

    (OUT_DIR / "_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nSaved to: {OUT_DIR}")
    print("Zip that folder (or the .json files) and hand it over. No token is included.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
