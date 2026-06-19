import os
import sys
import subprocess
import pytest
from datetime import datetime, timezone, timedelta
from scripts.check_commit_window import (
    parse_git_date, 
    check_commit_dates, 
    run_check, 
    CUTOFF_DATE
)

def test_parse_git_date_valid():
    dt = parse_git_date("2026-06-18 15:57:54 -0400")
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 18
    assert dt.hour == 15
    assert dt.minute == 57
    assert dt.second == 54
    assert dt.tzinfo.utcoffset(dt) == timedelta(hours=-4)

    dt2 = parse_git_date("2026-06-17 00:00:00 +0000")
    assert dt2.tzinfo.utcoffset(dt2) == timedelta(0)

def test_parse_git_date_invalid():
    with pytest.raises(ValueError):
        parse_git_date("2026-06-18 15:57:54")
    with pytest.raises(ValueError):
        parse_git_date("2026-06-18 15:57:54 -040")
    with pytest.raises(ValueError):
        parse_git_date("2026-06-18 15:57:54 -04000")

def test_check_commit_dates_all_valid():
    lines = [
        "2026-06-18 12:00:00 -0400 2026-06-18 12:00:00 -0400",
        "2026-06-17 00:00:00 +0000 2026-06-17 00:00:00 +0000"
    ]
    invalid = check_commit_dates(lines, CUTOFF_DATE)
    assert len(invalid) == 0

def test_check_commit_dates_invalid_author():
    lines = [
        "2026-06-16 23:59:59 +0000 2026-06-17 00:00:00 +0000"
    ]
    invalid = check_commit_dates(lines, CUTOFF_DATE)
    assert len(invalid) == 1
    assert invalid[0][0] == 0  # index of invalid commit

def test_check_commit_dates_invalid_commit():
    lines = [
        "2026-06-17 00:00:00 +0000 2026-06-16 23:59:59 +0000"
    ]
    invalid = check_commit_dates(lines, CUTOFF_DATE)
    assert len(invalid) == 1
    assert invalid[0][0] == 0

def test_check_commit_dates_timezone_boundaries():
    # 2026-06-16 22:00:00 -0400 has UTC instant of 2026-06-17 02:00:00 UTC (>= cutoff UTC instant),
    # but local date is 2026-06-16 which is before the cutoff. Symmetrically check rejection.
    line_local_invalid = "2026-06-16 22:00:00 -0400 2026-06-17 12:00:00 +0000"
    assert len(check_commit_dates([line_local_invalid], CUTOFF_DATE)) == 1

    # 2026-06-17 02:00:00 +0530 has local date of 2026-06-17 (valid),
    # but UTC instant is 2026-06-16 20:30:00 UTC (< cutoff UTC instant). Symmetrically check rejection.
    line_utc_invalid = "2026-06-17 02:00:00 +0530 2026-06-17 12:00:00 +0000"
    assert len(check_commit_dates([line_utc_invalid], CUTOFF_DATE)) == 1

    # Both valid
    line_valid = "2026-06-17 00:00:00 -0400 2026-06-17 00:00:00 -0400"
    assert len(check_commit_dates([line_valid], CUTOFF_DATE)) == 0

def test_run_check_exit_codes():
    # Valid commit lines -> exit code 0
    assert run_check("2026-06-18 12:00:00 -0400 2026-06-18 12:00:00 -0400") == 0
    # Invalid commit line -> exit code 1
    assert run_check("2026-06-16 12:00:00 -0400 2026-06-16 12:00:00 -0400") == 1
    # Empty git log stdout -> exit code 1
    assert run_check("") == 1
    assert run_check("\n") == 1
    # Malformed line -> exit code 1
    assert run_check("malformed line content") == 1

def test_cli_integration_clean(tmp_path):
    # Initialize a new git repository in a temp directory
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, capture_output=True, check=True)
    
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("hello")
    subprocess.run(["git", "add", "dummy.txt"], cwd=tmp_path, capture_output=True, check=True)
    
    # Commit with dates >= 2026-06-17
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-06-18T12:00:00 -0400",
        "GIT_COMMITTER_DATE": "2026-06-18T12:00:00 -0400"
    }
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, env=env, capture_output=True, check=True)
    
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "check_commit_window.py"))
    
    res = subprocess.run([sys.executable, script_path], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 0
    assert "All commits are within the allowed window" in res.stdout

def test_cli_integration_violation(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, capture_output=True, check=True)
    
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("hello")
    subprocess.run(["git", "add", "dummy.txt"], cwd=tmp_path, capture_output=True, check=True)
    
    # Commit before 2026-06-17
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-06-16T23:59:59 -0400",
        "GIT_COMMITTER_DATE": "2026-06-16T23:59:59 -0400"
    }
    subprocess.run(["git", "commit", "-m", "Backdated commit"], cwd=tmp_path, env=env, capture_output=True, check=True)
    
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "check_commit_window.py"))
    
    res = subprocess.run([sys.executable, script_path], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 1
    assert "CRITICAL: Commits found outside the allowed window" in res.stderr

def test_cli_integration_empty_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "check_commit_window.py"))
    
    res = subprocess.run([sys.executable, script_path], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 1
    assert "CRITICAL: No commits found in repository." in res.stderr
