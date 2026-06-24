import io
import os
import zipfile
import pytest
from fastapi.testclient import TestClient

from gdg_yorku_submission.schemas import CorpusFile, ReviewFinding, Location
from gdg_yorku_submission.severity import Severity, SEVERITY_FLOOR
from gdg_yorku_submission.orchestrator import InProcessOrchestrator
from gdg_yorku_submission.security.deterministic import (
    make_security_specialist,
    detect_languages,
)
from gdg_yorku_submission.app import app

client = TestClient(app)


def make_dummy_corpus_file(path: str, text: str, line_map=None) -> CorpusFile:
    lines = text.splitlines()
    line_count = len(lines)
    if line_map is None:
        line_map = {i: i for i in range(1, line_count + 1)}
    else:
        max_line = max(line_map.values())
        line_count = max(line_count, max_line)
    return CorpusFile(
        normalized_path=path,
        original_text=text,
        redacted_text=text,
        original_line_count=line_count,
        redacted_to_original_line_map=line_map,
        evidence_ref=f"file:{path}",
        exposure_status="prompt_exposed",
        ingest_status="success"
    )


def assert_finding_shape(f: ReviewFinding, sub_rule: str, path: str):
    """Utility to tighten assertions on the full finding shape (Issue 6 & 1)."""
    assert f.severity >= SEVERITY_FLOOR
    assert f.severity == Severity.HIGH
    assert f.status == "active"
    assert f.source_agent == "security_deterministic"
    assert f.perspective == "security"
    assert f.location.path == path
    assert f.location.line_start > 0
    assert f.location.line_end >= f.location.line_start
    assert len(f.evidence_ref) == 1
    assert f.evidence_ref[0] == f"file:{path}#{f.location.line_start}-{f.location.line_end}"
    assert f.metadata.get("rule_or_category") == "security_baseline"
    assert f.metadata.get("sub_rule") == sub_rule
    assert f.metadata.get("ast_node_id") is not None


def test_sqli_checker():
    # Vulnerable f-string SQLi
    code_vuln_fstring = """
def search_users(cursor, user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
"""
    # Vulnerable format SQLi
    code_vuln_format = """
def search_users(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))
"""
    # Vulnerable concatenation SQLi
    code_vuln_concat = """
def search_users(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
"""
    # Safe execute with string literal
    code_safe_literal = """
def search_users(cursor):
    cursor.execute("SELECT * FROM users")
"""
    # Safe execute with format string using literals
    code_safe_format = """
def search_users(cursor):
    cursor.execute("SELECT * FROM {}".format("users"))
"""

    corpus = {
        "vuln_fstring.py": make_dummy_corpus_file("vuln_fstring.py", code_vuln_fstring),
        "vuln_format.py": make_dummy_corpus_file("vuln_format.py", code_vuln_format),
        "vuln_concat.py": make_dummy_corpus_file("vuln_concat.py", code_vuln_concat),
        "safe_literal.py": make_dummy_corpus_file("safe_literal.py", code_safe_literal),
        "safe_format.py": make_dummy_corpus_file("safe_format.py", code_safe_format)
    }

    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 5, "total_bytes": 100})
    
    spec = make_security_specialist(orch)
    findings, _, _ = spec()

    sqli_findings = [f for f in findings if f.metadata.get("sub_rule") == "sqli"]
    assert len(sqli_findings) == 3
    
    # Assert no parse failures occurred (Issue 5 & 4)
    assert orch.read_state().get("run_metadata", {}).get("unparseable_file_count", 0) == 0

    # Tighten assertions on shape (Issue 6)
    for f in sqli_findings:
        assert_finding_shape(f, "sqli", f.location.path)


def test_shell_true_checker():
    code_vuln_sub = """
import subprocess
def ping(ip):
    subprocess.run(f"ping {ip}", shell=True)
"""
    code_vuln_os = """
import os
def ping(ip):
    os.system("ping " + ip)
"""
    code_safe_sub1 = """
import subprocess
def ping(ip):
    subprocess.run(["ping", ip])
"""
    code_safe_sub2 = """
import subprocess
def ping():
    subprocess.run("ping 8.8.8.8", shell=True)
"""
    code_safe_os = """
import os
def ping():
    os.system("ping 8.8.8.8")
"""

    corpus = {
        "vuln_sub.py": make_dummy_corpus_file("vuln_sub.py", code_vuln_sub),
        "vuln_os.py": make_dummy_corpus_file("vuln_os.py", code_vuln_os),
        "safe_sub1.py": make_dummy_corpus_file("safe_sub1.py", code_safe_sub1),
        "safe_sub2.py": make_dummy_corpus_file("safe_sub2.py", code_safe_sub2),
        "safe_os.py": make_dummy_corpus_file("safe_os.py", code_safe_os)
    }

    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 5, "total_bytes": 100})
    
    spec = make_security_specialist(orch)
    findings, _, _ = spec()

    shell_findings = [f for f in findings if f.metadata.get("sub_rule") == "shell_true"]
    assert len(shell_findings) == 2
    assert orch.read_state().get("run_metadata", {}).get("unparseable_file_count", 0) == 0

    for f in shell_findings:
        assert_finding_shape(f, "shell_true", f.location.path)


def test_unsafe_deserialize():
    code_vuln_pickle = """
import pickle
def load_data(data):
    return pickle.loads(data)
"""
    code_vuln_yaml = """
import yaml
def load_config(config_str):
    return yaml.load(config_str)
"""
    code_safe_yaml1 = """
import yaml
def load_config(config_str):
    return yaml.safe_load(config_str)
"""
    code_safe_yaml2 = """
import yaml
def load_config(config_str):
    return yaml.load(config_str, Loader=yaml.SafeLoader)
"""
    # Issue 8: Negative check ensuring bare json.loads is NOT flagged
    code_safe_json = """
import json
def load_json(json_str):
    return json.loads(json_str)
"""

    corpus = {
        "vuln_pickle.py": make_dummy_corpus_file("vuln_pickle.py", code_vuln_pickle),
        "vuln_yaml.py": make_dummy_corpus_file("vuln_yaml.py", code_vuln_yaml),
        "safe_yaml1.py": make_dummy_corpus_file("safe_yaml1.py", code_safe_yaml1),
        "safe_yaml2.py": make_dummy_corpus_file("safe_yaml2.py", code_safe_yaml2),
        "safe_json.py": make_dummy_corpus_file("safe_json.py", code_safe_json)
    }

    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 5, "total_bytes": 100})
    
    spec = make_security_specialist(orch)
    findings, _, _ = spec()

    deserialize_findings = [f for f in findings if f.metadata.get("sub_rule") == "unsafe_deserialize"]
    assert len(deserialize_findings) == 2
    assert orch.read_state().get("run_metadata", {}).get("unparseable_file_count", 0) == 0

    for f in deserialize_findings:
        assert_finding_shape(f, "unsafe_deserialize", f.location.path)
    
    paths = {f.location.path for f in deserialize_findings}
    assert "vuln_pickle.py" in paths
    assert "vuln_yaml.py" in paths
    assert "safe_json.py" not in paths


def test_missing_auth():
    code_vuln_flask = """
@app.route("/delete-user", methods=["POST"])
def delete_user():
    pass
"""
    code_vuln_fastapi = """
@router.post("/delete-user")
def delete_user():
    pass
"""
    code_safe_flask_get = """
@app.route("/get-user")
def get_user():
    pass
"""
    # Issue 4: Fixed stray backticks inside the python string to allow parsing
    code_safe_flask_auth = """
@app.post("/delete-user")
@requires_jwt_auth
def delete_user():
    pass
"""
    # Issue 10: negative unit check for non-standard auth decorators
    code_safe_custom_auth = """
@app.post("/delete-user")
@protected
def delete_user():
    pass
"""
    code_safe_fastapi_depends = """
from fastapi import Depends
@router.post("/delete-user")
def delete_user(current_user: User = Depends(get_current_user)):
    pass
"""

    corpus = {
        "vuln_flask.py": make_dummy_corpus_file("vuln_flask.py", code_vuln_flask),
        "vuln_fastapi.py": make_dummy_corpus_file("vuln_fastapi.py", code_vuln_fastapi),
        "safe_flask_get.py": make_dummy_corpus_file("safe_flask_get.py", code_safe_flask_get),
        "safe_flask_auth.py": make_dummy_corpus_file("safe_flask_auth.py", code_safe_flask_auth),
        "safe_custom_auth.py": make_dummy_corpus_file("safe_custom_auth.py", code_safe_custom_auth),
        "safe_fastapi_depends.py": make_dummy_corpus_file("safe_fastapi_depends.py", code_safe_fastapi_depends),
    }

    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 6, "total_bytes": 100})
    
    spec = make_security_specialist(orch)
    findings, _, _ = spec()

    auth_findings = [f for f in findings if f.metadata.get("sub_rule") == "missing_auth"]
    assert len(auth_findings) == 2
    assert orch.read_state().get("run_metadata", {}).get("unparseable_file_count", 0) == 0

    for f in auth_findings:
        assert_finding_shape(f, "missing_auth", f.location.path)
    
    paths = {f.location.path for f in auth_findings}
    assert "vuln_flask.py" in paths
    assert "vuln_fastapi.py" in paths


def test_path_traversal():
    code_vuln_open = """
@app.route("/read-file")
def read_file(filename):
    with open(filename, "r") as f:
        return f.read()
"""
    # Issue 7 (a): Avoid bare string.join() method collision
    code_safe_string_join = """
@app.route("/join-strings")
def join_strings(parts):
    return "-".join(parts)
"""
    # Issue 7 (b): Targeted normalize check (open(other_filename) should still be flagged)
    code_vuln_targeted_check = """
import os
@app.route("/read-file")
def read_file(filename, other_filename):
    real_path = os.path.realpath(filename)
    if real_path.startswith("/var/data"):
        # filename is safe, but other_filename is not
        with open(other_filename, "r") as f:
            return f.read()
"""

    corpus = {
        "vuln_open.py": make_dummy_corpus_file("vuln_open.py", code_vuln_open),
        "safe_string_join.py": make_dummy_corpus_file("safe_string_join.py", code_safe_string_join),
        "vuln_targeted_check.py": make_dummy_corpus_file("vuln_targeted_check.py", code_vuln_targeted_check)
    }

    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 3, "total_bytes": 100})
    
    spec = make_security_specialist(orch)
    findings, _, _ = spec()

    traversal_findings = [f for f in findings if f.metadata.get("sub_rule") == "path_traversal"]
    assert len(traversal_findings) == 2
    assert orch.read_state().get("run_metadata", {}).get("unparseable_file_count", 0) == 0

    for f in traversal_findings:
        assert_finding_shape(f, "path_traversal", f.location.path)
        
    paths = {f.location.path for f in traversal_findings}
    assert "vuln_open.py" in paths
    assert "vuln_targeted_check.py" in paths
    assert "safe_string_join.py" not in paths


def test_path_traversal_precision():
    # Issue 7 Taint tracking: intermediate assignment and unrelated check bypass
    code_text = """
import os
@app.route("/read")
def read(user_input, mode):
    # Assignment without normalization:
    tainted_var = user_input
    
    # Unrelated check (should not suppress tainted_var vuln)
    if mode.startswith("r"):
        pass
        
    with open(tainted_var) as f:
        pass
"""
    # Nested path call suppression test (Issue 11 / point 1)
    code_nested = """
import os
@app.route("/read-nested")
def read_nested(user_input):
    with open(os.path.join("/base", user_input)) as f:
        pass
"""

    corpus = {
        "src/api.py": make_dummy_corpus_file("src/api.py", code_text),
        "src/nested.py": make_dummy_corpus_file("src/nested.py", code_nested)
    }
    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 2, "total_bytes": 100})
    findings, _, _ = make_security_specialist(orch)()
    
    # One finding from src/api.py, and exactly one finding from src/nested.py (the inner join was suppressed)
    traversal_findings = [f for f in findings if f.metadata.get("sub_rule") == "path_traversal"]
    assert len(traversal_findings) == 2
    
    paths = {f.location.path for f in traversal_findings}
    assert "src/api.py" in paths
    assert "src/nested.py" in paths


def test_verify_false():
    code_vuln = """
import requests
def fetch_url(url):
    return requests.get(url, verify=False)
"""
    # Issue 9: Custom validator call with verify=False must NOT be flagged
    code_safe_custom = """
def my_validator(data, verify=False):
    pass
"""

    corpus = {
        "vuln.py": make_dummy_corpus_file("vuln.py", code_vuln),
        "safe_custom.py": make_dummy_corpus_file("safe_custom.py", code_safe_custom)
    }

    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 2, "total_bytes": 100})
    
    spec = make_security_specialist(orch)
    findings, _, _ = spec()

    verify_findings = [f for f in findings if f.metadata.get("sub_rule") == "verify_false"]
    assert len(verify_findings) == 1
    assert orch.read_state().get("run_metadata", {}).get("unparseable_file_count", 0) == 0

    assert_finding_shape(verify_findings[0], "verify_false", "vuln.py")


def test_verify_false_imports():
    # Issue 9: verify=False HTTP imports verification
    code_text = """
from requests import get
def run():
    get("url", verify=False)
"""
    corpus = {
        "src/run.py": make_dummy_corpus_file("src/run.py", code_text)
    }
    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 1, "total_bytes": 100})
    findings, _, _ = make_security_specialist(orch)()
    assert len(findings) == 1
    assert findings[0].metadata.get("sub_rule") == "verify_false"


def test_original_coordinate_mapping():
    # Issue 2: Verify non-identity coordinate mapping back to original line numbers
    code_text = """# Header line
import requests
def fetch(url):
    return requests.get(url, verify=False)
"""
    # Simulate a map where redacted line 4 corresponds to original line 99
    line_map = {1: 1, 2: 2, 3: 3, 4: 99}
    corpus = {
        "src/api.py": make_dummy_corpus_file("src/api.py", code_text, line_map=line_map)
    }

    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 1, "total_bytes": 100})

    spec = make_security_specialist(orch)
    findings, _, _ = spec()

    assert len(findings) == 1
    finding = findings[0]
    assert finding.location.path == "src/api.py"
    assert finding.location.line_start == 99
    assert finding.location.line_end == 99
    assert finding.evidence_ref == ["file:src/api.py#99-99"]


def test_id_stability_and_collision():
    # Issue 3: Pinned determinism of security finding IDs + Prove ordinal/merge edge
    code_text = """
import requests
import pickle
def execute_rules(data):
    # Two distinct findings on the exact same line (verify=False and unsafe_deserialize)
    pickle.loads(data); requests.post("https://url", verify=False)
"""
    corpus = {
        "src/run.py": make_dummy_corpus_file("src/run.py", code_text)
    }

    # Run 1
    orch1 = InProcessOrchestrator()
    orch1.start_run()
    orch1.set_corpus(corpus)
    orch1.set_corpus_summary({"file_count": 1, "total_bytes": 100})
    orch1.run_specialist("security", make_security_specialist(orch1))
    report1 = orch1.compile_report()

    # Run 2
    orch2 = InProcessOrchestrator()
    orch2.start_run()
    orch2.set_corpus(corpus)
    orch2.set_corpus_summary({"file_count": 1, "total_bytes": 100})
    orch2.run_specialist("security", make_security_specialist(orch2))
    report2 = orch2.compile_report()

    # Verify ID Stability: identical runs yield identical finalized IDs
    ids1 = sorted([f.id for f in report1.findings])
    ids2 = sorted([f.id for f in report2.findings])
    assert len(ids1) == 2
    assert ids1 == ids2
    for fid in ids1:
        assert len(fid) == 64  # deterministic SHA-256 finalized ID

    # Verify ID Ordinal/Merge: different rule/category yields distinct ordinals/IDs rather than merging
    perspectives = [f.metadata.get("sub_rule") for f in report1.findings]
    assert "unsafe_deserialize" in perspectives
    assert "verify_false" in perspectives


def test_id_stability_and_collision_same_rule():
    # Issue 3: Two distinct verify=False calls on different redacted lines mapped to same original line
    code_text = """
import requests
def run():
    requests.get("url1", verify=False)
    requests.get("url2", verify=False)
"""
    line_map = {1:1, 2:2, 3:3, 4:99, 5:99}
    corpus = {
        "src/run.py": make_dummy_corpus_file("src/run.py", code_text, line_map=line_map)
    }
    
    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 1, "total_bytes": 100})
    orch.run_specialist("security", make_security_specialist(orch))
    report = orch.compile_report()
    
    # Since they have identical rule and map to identical original line with identical col_offset, they merge
    assert len(report.findings) == 1
    f = report.findings[0]
    assert "SSL verification disabled" in f.claim
    assert len(f.evidence_ref) == 1  # Deduplicated to same coordinate
    assert len(f.metadata.get("merged_from_provisional", [])) == 2



def test_id_stability_and_collision_same_rule_different_cols():
    # Issue 3: Different col_offsets on same original line should ordinal instead of merge
    code_text = """
import requests
def run():
    requests.get("url1", verify=False); requests.get("url2", verify=False)
"""
    line_map = {1:1, 2:2, 3:3, 4:99}
    corpus = {
        "src/run.py": make_dummy_corpus_file("src/run.py", code_text, line_map=line_map)
    }
    
    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 1, "total_bytes": 100})
    orch.run_specialist("security", make_security_specialist(orch))
    report = orch.compile_report()
    
    assert len(report.findings) == 2
    assert report.findings[0].id != report.findings[1].id


def test_parse_failure_swallowing():
    # Issue 5: Ensure unparseable file syntax errors are surfaced in status & reason
    broken_code = """
def broken_syntax(
"""
    corpus = {
        "src/broken.py": make_dummy_corpus_file("src/broken.py", broken_code),
        "src/safe.py": make_dummy_corpus_file("src/safe.py", "print(1)")
    }

    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 2, "total_bytes": 100})

    orch.run_specialist("security", make_security_specialist(orch))
    report = orch.compile_report()

    sec_status = next(s for s in report.perspective_statuses if s.perspective == "security")
    assert sec_status.status == "complete_limited"
    assert "syntax errors in src/broken.py" in sec_status.reason
    assert report.run_metadata["unparseable_file_count"] == 1


def test_scan_scope_isolation():
    # Issue 13: Verify that ignored files are NOT scanned for security violations or language detection
    vuln_code = """
import requests
def fetch(url):
    return requests.get(url, verify=False)
"""
    exposed_file = make_dummy_corpus_file("src/main.py", "print(1)")
    ignored_file = make_dummy_corpus_file("config/vuln.py", vuln_code)
    ignored_file.exposure_status = "ignored_by_root_gitignore"

    corpus = {
        "src/main.py": exposed_file,
        "config/vuln.py": ignored_file
    }

    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 2, "total_bytes": 100})

    orch.run_specialist("security", make_security_specialist(orch))
    report = orch.compile_report()

    # The ignored file contains verify=False but should NOT be scanned
    assert len(report.findings) == 0

    # Test language detection ignores ignored files
    corpus_mixed = {
        "src/main.py": exposed_file,
        "ignored_lib.go": make_dummy_corpus_file("ignored_lib.go", "package main")
    }
    corpus_mixed["ignored_lib.go"].exposure_status = "ignored_by_root_gitignore"

    langs, count = detect_languages(corpus_mixed)
    assert count == 0
    assert len(langs) == 0


def test_language_detection_unit():
    corpus_py = {
        "src/main.py": make_dummy_corpus_file("src/main.py", "print(1)"),
        "README.md": make_dummy_corpus_file("README.md", "# Test"),
        "config.json": make_dummy_corpus_file("config.json", "{}")
    }
    langs_py, count_py = detect_languages(corpus_py)
    assert count_py == 0
    assert len(langs_py) == 0

    corpus_mixed = {
        "src/main.py": make_dummy_corpus_file("src/main.py", "print(1)"),
        "src/app.go": make_dummy_corpus_file("src/app.go", "package main"),
        "src/Main.java": make_dummy_corpus_file("src/Main.java", "public class Main {}"),
        "src/lib.cpp": make_dummy_corpus_file("src/lib.cpp", "int main() {}"),
        "README.md": make_dummy_corpus_file("README.md", "# Test")
    }
    langs_mixed, count_mixed = detect_languages(corpus_mixed)
    assert count_mixed == 3
    assert langs_mixed == ["cpp", "go", "java"]


def test_custom_status_override():
    corpus_mixed = {
        "src/main.py": make_dummy_corpus_file("src/main.py", "print(1)"),
        "src/app.go": make_dummy_corpus_file("src/app.go", "package main"),
        "src/Main.java": make_dummy_corpus_file("src/Main.java", "public class Main {}"),
    }
    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus_mixed)
    orch.set_corpus_summary({"file_count": 3, "total_bytes": 100})

    orch.run_specialist("security", make_security_specialist(orch))

    report = orch.compile_report()
    sec_status = next(s for s in report.perspective_statuses if s.perspective == "security")
    
    assert sec_status.status == "complete_limited"
    assert "no deterministic rules for go, java" in sec_status.reason
    assert report.run_metadata["unsupported_language_count"] == 2


def test_specialist_arity_failure():
    # Issue 14: Specialist returns a 2-tuple instead of a 3-tuple
    def bad_specialist():
        return ([], "complete")  # length 2
        
    orch = InProcessOrchestrator()
    orch.start_run()
    
    orch.run_specialist("security", bad_specialist)
    state = orch.read_state()
    status = state["perspective_statuses"]["security"]
    assert status.status == "failed"
    assert "expected exactly 3" in status.reason


def test_api_e2e_security():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        vuln_code = """
import requests
def fetch():
    return requests.post("https://example.com", verify=False)
"""
        z.writestr("vuln.py", vuln_code)
    zip_bytes = buf.getvalue()

    files = {"file": ("test.zip", zip_bytes, "application/zip")}
    response = client.post("/review", files=files)
    assert response.status_code == 200

    report = response.json()
    # /review always drives the ADK orchestrator (which falls back to in-process
    # behavior internally if ADK is unavailable, but keeps its class name).
    assert report["run_metadata"]["orchestrator_type"] == "AdkOrchestrator"

    findings = report["findings"]
    sec_findings = [f for f in findings if f["perspective"] == "security"]
    
    assert len(sec_findings) == 1
    finding = sec_findings[0]
    assert finding["source_agent"] == "security_deterministic"
    assert finding["severity"] == "high"
    assert finding["location"]["path"] == "vuln.py"
    assert "SSL verification disabled" in finding["claim"]
    assert len(finding["id"]) == 64
