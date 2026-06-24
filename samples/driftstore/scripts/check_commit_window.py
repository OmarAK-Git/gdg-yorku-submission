#!/usr/bin/env python3
import sys
import subprocess
from datetime import datetime, timezone, timedelta

# Single source of truth for the cutoff window
CUTOFF_DATE = datetime(2026, 6, 17, 0, 0, 0, tzinfo=timezone.utc)

def parse_git_date(date_str: str) -> datetime:
    """
    Parses a git date string in format "YYYY-MM-DD HH:MM:SS TZ" (e.g., "2026-06-18 15:57:54 -0400")
    into a timezone-aware datetime object.
    """
    parts = date_str.strip().split()
    if len(parts) != 3:
        raise ValueError(f"Unexpected date format: {date_str}")
    
    dt_str = f"{parts[0]} {parts[1]}"
    tz_str = parts[2]
    
    if len(tz_str) != 5 or tz_str[0] not in ('+', '-'):
        raise ValueError(f"Unexpected timezone format: {tz_str}")
        
    sign = 1 if tz_str[0] == '+' else -1
    hours = int(tz_str[1:3])
    minutes = int(tz_str[3:5])
    tz = timezone(timedelta(hours=sign * hours, minutes=sign * minutes))
    
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=tz)

def check_commit_dates(lines: list[str], cutoff: datetime) -> list[tuple[int, datetime, datetime]]:
    """
    Checks list of '%ai %ci' lines against the cutoff datetime.
    Returns a list of tuples: (index, author_dt, commit_dt) for invalid commits.
    Checks BOTH UTC instant and the local/displayed calendar date.
    """
    invalid_commits = []
    cutoff_date = cutoff.date()
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        parts = line.split()
        if len(parts) != 6:
            raise ValueError(f"Malformed git log line {i+1}: {line}")
            
        author_date_str = " ".join(parts[0:3])
        commit_date_str = " ".join(parts[3:6])
        
        author_dt = parse_git_date(author_date_str)
        commit_dt = parse_git_date(commit_date_str)
        
        author_utc = author_dt.astimezone(timezone.utc)
        commit_utc = commit_dt.astimezone(timezone.utc)
        
        # Safe/conservative check: both the UTC instant AND the local/displayed calendar date
        # must be equal or after the cutoff.
        author_invalid = author_utc < cutoff or author_dt.date() < cutoff_date
        commit_invalid = commit_utc < cutoff or commit_dt.date() < cutoff_date
        
        if author_invalid or commit_invalid:
            invalid_commits.append((i, author_dt, commit_dt))
            
    return invalid_commits

def run_check(git_log_stdout: str) -> int:
    """
    Helper to run the checks on raw git log output and return an exit code.
    """
    lines = git_log_stdout.strip().split('\n')
    if not lines or (len(lines) == 1 and lines[0] == ''):
        print("CRITICAL: No commits found in repository.", file=sys.stderr)
        return 1

    try:
        invalid_commits = check_commit_dates(lines, CUTOFF_DATE)
    except ValueError as e:
        print(f"CRITICAL: {e}", file=sys.stderr)
        return 1
            
    if invalid_commits:
        print("CRITICAL: Commits found outside the allowed window (>= 2026-06-17)!", file=sys.stderr)
        for idx, author_dt, commit_dt in invalid_commits:
            print(f"  Commit #{idx+1} (reverse chronological):", file=sys.stderr)
            print(f"    Author Date (local): {author_dt.isoformat()}", file=sys.stderr)
            print(f"    Commit Date (local): {commit_dt.isoformat()}", file=sys.stderr)
        return 1
        
    print("All commits are within the allowed window (>= 2026-06-17).")
    return 0

def main():
    try:
        # Walk all refs (branches, tags) via git log --all to verify all commit history
        result = subprocess.run(
            ["git", "log", "--all", "--format=%ai %ci"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running git log: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Git command not found.", file=sys.stderr)
        sys.exit(1)

    exit_code = run_check(result.stdout)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
