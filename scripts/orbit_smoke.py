"""
Live Orbit connectivity + blast-radius smoke test.

Loads `.env` (zero-dependency parser), hits the real Orbit graph_query API with
the credentials there, and prints what comes back. Crucially it also prints the
definitions/calls coordinate-join diagnostic, which is where live results silently
under-count (the mock test suite cannot see this because its fixtures overlap
perfectly).

Usage (PowerShell):
    python scripts/orbit_smoke.py

Place your token in `.env` first (gitignored). To avoid the token landing in
shell history, you can create the file from the session prompt with the `!`
prefix rather than typing it here.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


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
        # Real environment wins over .env so shell exports can override.
        os.environ.setdefault(key, val)


def main() -> int:
    load_dotenv(ROOT / ".env")

    from gdg_yorku_submission.blast_radius.orbit_client import OrbitClient

    client = OrbitClient()
    print(f"api_url       = {client.api_url}")
    print(f"project_path  = {client.project_path}")
    print(f"token set     = {bool(client.api_token)}")
    print(f"use_fake      = {client.use_fake}")

    if not client.is_configured():
        print("\nNOT CONFIGURED. Fill ORBIT_API_URL / ORBIT_API_TOKEN / ORBIT_PROJECT_PATH in .env")
        return 2

    print("\nhealth_check ...", end=" ")
    ok = client.health_check()
    print("OK" if ok else "FAILED")
    if not ok:
        print("Orbit unreachable or project not found. Check URL/token/project_path.")
        return 3

    fetchers = [
        ("definitions", client.fetch_definitions),
        ("calls", client.fetch_calls),
        ("imports", client.fetch_imports),
        ("vulnerabilities", client.fetch_vulnerabilities),
        ("pipelines", client.fetch_pipelines),
        ("merge_requests", client.fetch_merge_requests),
    ]
    results = {}
    for name, fn in fetchers:
        try:
            res = fn()
            results[name] = res
            print(f"  {name:16s} row_count={res.row_count} nodes={len(res.nodes)} edges={len(res.edges)}")
        except Exception as e:  # noqa: BLE001 - surface any live failure
            results[name] = None
            print(f"  {name:16s} ERROR: {type(e).__name__}: {e}")

    # --- The join diagnostic: how many blast targets can we actually locate? ---
    defs, calls = results.get("definitions"), results.get("calls")
    if defs is not None and calls is not None:
        defs_with_coords = {
            n.id for n in defs.nodes_of_type("Definition") if n.get("file_path")
        } | {
            n.id for n in calls.nodes_of_type("Definition") if n.get("file_path")
        }
        call_edges = calls.edges_of_type("CALLS")
        targets = {e.to_id for e in call_edges if e.to_id}
        locatable = targets & defs_with_coords
        print("\n--- coordinate-join diagnostic ---")
        print(f"CALLS edges                : {len(call_edges)}")
        print(f"distinct blast targets     : {len(targets)}")
        print(f"targets with coords        : {len(locatable)}")
        dropped = len(targets) - len(locatable)
        if targets:
            print(f"SILENTLY DROPPED           : {dropped} ({dropped * 100 // max(1, len(targets))}%)")
        if dropped:
            print("=> fetch_calls should carry coords for src/dst so targets don't depend")
            print("   on a separate definitions join. See gate finding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
