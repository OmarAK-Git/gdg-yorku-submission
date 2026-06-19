import os
import tempfile
import pytest
from pathlib import Path
import pathspec
from gdg_yorku_submission.schemas import IngestionManifest, SkippedEntry, CorpusFile
from gdg_yorku_submission.corpus import (
    load_root_gitignore,
    classify_exposure,
    build_corpus,
    get_prompt_corpus,
)

def test_load_root_gitignore_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = load_root_gitignore(tmpdir)
        assert isinstance(spec, pathspec.PathSpec)
        assert not spec.match_file("test.py")

def test_load_root_gitignore_valid():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Note on V1 Pathspec/Gitignore re-inclusion behavior:
        # Real Git does not allow re-inclusion under an ignored directory (e.g. if 'secret/' is ignored,
        # negation '!secret/keep.log' has no effect because Git stops scanning the directory).
        # However, for root-only wildmatch matching in pathspec without tree scanning,
        # matching against the raw paths honors the negation directly. This is an accepted V1 divergence.
        gitignore_content = """
# this is a comment
*.log
secret/
!secret/keep.log
"""
        with open(os.path.join(tmpdir, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(gitignore_content)
            
        spec = load_root_gitignore(tmpdir)
        assert spec.match_file("error.log")
        assert spec.match_file("secret/passwords.txt")
        # Negation is honored by pathspec's match logic
        assert not spec.match_file("secret/keep.log")
        assert not spec.match_file("src/main.py")

def test_classify_exposure():
    spec = pathspec.PathSpec.from_lines("gitignore", ["*.env", "ignored.txt"])
    
    # 1. prompt_exposed (not skipped, not matched)
    status = classify_exposure("src/main.py", False, spec)
    assert status == "prompt_exposed"
    
    # 2. ignored_by_root_gitignore (not skipped, matched)
    status = classify_exposure("config.env", False, spec)
    assert status == "ignored_by_root_gitignore"
    
    # 3. excluded_by_system (skipped due to system exclude/binary)
    status = classify_exposure(".venv/lib/x.py", True, spec)
    assert status == "excluded_by_system"
    
    status = classify_exposure("db.sqlite", True, spec)
    assert status == "excluded_by_system"

    # 4. security_skip (maps to excluded_by_system for trust boundary / spec compliance)
    status = classify_exposure("nested.zip", True, spec)
    assert status == "excluded_by_system"

    status = classify_exposure("../escaped.txt", True, spec)
    assert status == "excluded_by_system"

def test_corpus_file_line_map():
    cf = CorpusFile(
        normalized_path="src/main.py",
        original_text="line 1\nline 2\nline 3",
        redacted_text="line 1\n[REDACTED]\nline 3",
        original_line_count=3,
        redacted_to_original_line_map={1: 1, 2: 2, 3: 3},
        evidence_ref="file:src/main.py",
        exposure_status="prompt_exposed",
        ingest_status="success"
    )
    
    assert cf.map_line(1) == 1
    assert cf.map_line(2) == 2
    assert cf.map_line(3) == 3
    assert cf.map_line(4) == 4

def test_corpus_file_shifted_line_map():
    # Verify that map_line consults the dictionary and handles line shifts/deletions
    cf = CorpusFile(
        normalized_path="src/main.py",
        original_text="line 1\nline 2\nline 3",
        redacted_text="line 1\nline 3",
        original_line_count=3,
        redacted_to_original_line_map={1: 1, 2: 3},
        evidence_ref="file:src/main.py",
        exposure_status="prompt_exposed",
        ingest_status="success"
    )
    
    assert cf.map_line(1) == 1
    assert cf.map_line(2) == 3 # Line 2 in redacted maps to Line 3 in original

def test_corpus_file_empty_line_map():
    cf = CorpusFile(
        normalized_path="src/main.py",
        original_text="line 1\nline 2",
        redacted_text="line 1\nline 2",
        original_line_count=2,
        redacted_to_original_line_map={},
        evidence_ref="file:src/main.py",
        exposure_status="prompt_exposed",
        ingest_status="success"
    )
    
    assert cf.map_line(1) == 1
    assert cf.map_line(2) == 2

def test_build_corpus_happy_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        
        with open(os.path.join(tmpdir, "src/main.py"), "w", encoding="utf-8") as f:
            f.write("print('hello')\nprint('world')")
            
        with open(os.path.join(tmpdir, "secret.env"), "w", encoding="utf-8") as f:
            f.write("API_KEY=12345")
            
        with open(os.path.join(tmpdir, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("secret.env\n*.db\n")
            
        manifest = IngestionManifest(
            extracted_files=["src/main.py", "secret.env"],
            skipped_files={
                "database.db": SkippedEntry(skipped_reason="Binary file extension"),
                ".venv/x.py": SkippedEntry(skipped_reason="System exclude directory"),
                "../escaped.txt": SkippedEntry(skipped_reason="Path traversal attempt"),
            },
            total_extracted_bytes=100,
            total_extracted_count=2
        )
        
        corpus = build_corpus(tmpdir, manifest)
        
        # Verify extracted files are present
        assert "src/main.py" in corpus
        assert "secret.env" in corpus
        
        f1 = corpus["src/main.py"]
        assert f1.normalized_path == "src/main.py"
        assert f1.original_text == "print('hello')\nprint('world')"
        assert f1.original_line_count == 2
        assert f1.redacted_to_original_line_map == {1: 1, 2: 2}
        assert f1.exposure_status == "prompt_exposed"
        assert f1.ingest_status == "success"
        assert f1.evidence_ref == "file:src/main.py"
        
        f2 = corpus["secret.env"]
        assert f2.normalized_path == "secret.env"
        assert f2.original_text == "API_KEY=12345"
        assert f2.original_line_count == 1
        assert f2.redacted_to_original_line_map == {1: 1}
        assert f2.exposure_status == "ignored_by_root_gitignore"
        assert f2.ingest_status == "success"
        assert f2.evidence_ref == "file:secret.env"

        # Verify skipped files are present and correctly classified
        assert "database.db" in corpus
        assert ".venv/x.py" in corpus
        assert "../escaped.txt" in corpus

        db_file = corpus["database.db"]
        assert db_file.exposure_status == "excluded_by_system"
        assert db_file.ingest_status == "success"  # System exclude
        assert db_file.original_text == ""
        assert db_file.original_line_count == 0
        assert db_file.evidence_ref == "file:database.db"

        venv_file = corpus[".venv/x.py"]
        assert venv_file.exposure_status == "excluded_by_system"
        assert venv_file.ingest_status == "success"  # System exclude

        escaped_file = corpus["../escaped.txt"]
        assert escaped_file.exposure_status == "excluded_by_system"
        assert escaped_file.ingest_status == "security_skip"  # Security skip
        assert escaped_file.original_text == ""
        assert escaped_file.original_line_count == 0

def test_windows_path_normalization():
    spec = pathspec.PathSpec.from_lines("gitignore", ["ignored.txt"])
    status = classify_exposure("subdir\\ignored.txt", False, spec)
    assert status == "ignored_by_root_gitignore"

def test_build_corpus_determinism():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "a.py"), "w") as f:
            f.write("a = 1")
        with open(os.path.join(tmpdir, "b.py"), "w") as f:
            f.write("b = 2")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write("b.py")
            
        manifest = IngestionManifest(
            extracted_files=["a.py", "b.py"],
            skipped_files={"c.db": SkippedEntry(skipped_reason="Binary file extension")},
            total_extracted_bytes=10,
            total_extracted_count=2
        )
        
        c1 = build_corpus(tmpdir, manifest)
        c2 = build_corpus(tmpdir, manifest)
        
        assert c1.keys() == c2.keys()
        for k in c1:
            assert c1[k].exposure_status == c2[k].exposure_status
            assert c1[k].ingest_status == c2[k].ingest_status
            assert c1[k].original_text == c2[k].original_text
            assert c1[k].evidence_ref == c2[k].evidence_ref

def test_read_failure_handling():
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = IngestionManifest(
            extracted_files=["missing_file.py"],
            skipped_files={},
            total_extracted_bytes=0,
            total_extracted_count=1
        )
        corpus = build_corpus(tmpdir, manifest)
        
        assert "missing_file.py" in corpus
        missing_entry = corpus["missing_file.py"]
        assert missing_entry.exposure_status == "excluded_by_system"
        assert missing_entry.ingest_status == "read_failure"
        assert missing_entry.original_text == ""
        assert missing_entry.original_line_count == 0
        assert missing_entry.redacted_to_original_line_map == {}

def test_prompt_scope_filtering():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, "src/main.py"), "w") as f:
            f.write("print('ok')")
        with open(os.path.join(tmpdir, "secret.env"), "w") as f:
            f.write("KEY=val")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write("secret.env\n")

        manifest = IngestionManifest(
            extracted_files=["src/main.py", "secret.env"],
            skipped_files={"database.db": SkippedEntry(skipped_reason="Binary file extension")},
            total_extracted_bytes=20,
            total_extracted_count=2
        )

        corpus = build_corpus(tmpdir, manifest)
        
        # Verify full corpus contains everything
        assert "src/main.py" in corpus
        assert "secret.env" in corpus
        assert "database.db" in corpus

        # Filter to prompt corpus
        prompt_corp = get_prompt_corpus(corpus)
        
        # Assert ignored and skipped files are absent from prompt scope
        assert "src/main.py" in prompt_corp
        assert "secret.env" not in prompt_corp
        assert "database.db" not in prompt_corp

def test_non_utf8_tolerant_read():
    # Verify that latin-1 files are read tolerantly and not treated as read failure (N2)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Construct Latin-1 file content containing a secret
        file_content = b'SECRET = "cl\xe9_api..."' # latin-1 encoded
        
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, "src/config.py"), "wb") as f:
            f.write(file_content)
            
        manifest = IngestionManifest(
            extracted_files=["src/config.py"],
            skipped_files={},
            total_extracted_bytes=len(file_content),
            total_extracted_count=1
        )
        
        corpus = build_corpus(tmpdir, manifest)
        
        assert "src/config.py" in corpus
        entry = corpus["src/config.py"]
        assert entry.ingest_status == "success"
        assert entry.exposure_status == "prompt_exposed"
        # The character \xe9 is \xe9 in Latin-1 (é), but replaced or parsed tolerantly
        assert "cl" in entry.original_text
        assert "_api" in entry.original_text

def test_path_collision_prevention():
    # Verify that path collisions raise ValueError to prevent silent overwriting (N4)
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = IngestionManifest(
            extracted_files=["main.py"],
            skipped_files={"main.py": SkippedEntry(skipped_reason="Binary file extension")},
            total_extracted_bytes=0,
            total_extracted_count=1
        )
        
        with pytest.raises(ValueError, match="Duplicate path in corpus"):
            build_corpus(tmpdir, manifest)
