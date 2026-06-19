import pytest
import io
import zipfile
import os
import tempfile
import zlib
from pathlib import Path
from gdg_yorku_submission.ingestion import (
    HardenedZipExtractor,
    IngestionError,
    MAX_COMPRESSED_BYTES,
    MAX_UNCOMPRESSED_BYTES,
    MAX_FILE_COUNT,
    MAX_PER_FILE_BYTES
)

def create_in_memory_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for fname, content in files.items():
            z.writestr(fname, content)
    return buf.getvalue()

def test_valid_extraction():
    content = create_in_memory_zip({
        "src/main.py": b"print('hello world')",
        "README.md": b"# Doc",
    })
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = HardenedZipExtractor.extract(content, tmpdir)
        
        assert "src/main.py" in manifest.extracted_files
        assert "README.md" in manifest.extracted_files
        assert manifest.total_extracted_count == 2
        assert manifest.total_extracted_bytes == len(b"print('hello world')") + len(b"# Doc")
        
        assert os.path.exists(os.path.join(tmpdir, "src", "main.py"))

def test_compressed_size_cap():
    large_content = b"x" * (MAX_COMPRESSED_BYTES + 1)
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(IngestionError, match="Compressed size"):
            HardenedZipExtractor.extract(large_content, tmpdir)

def test_file_count_bomb(monkeypatch):
    content = create_in_memory_zip({f"file_{i}.txt": b"test" for i in range(5)})
    monkeypatch.setattr("gdg_yorku_submission.ingestion.MAX_FILE_COUNT", 3)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(IngestionError, match="Total file count exceeds cap"):
            HardenedZipExtractor.extract(content, tmpdir)

def test_uncompressed_size_cap(monkeypatch):
    content = create_in_memory_zip({
        "large_file.txt": b"a" * 1000,
        "large_file_2.txt": b"b" * 1000
    })
    monkeypatch.setattr("gdg_yorku_submission.ingestion.MAX_UNCOMPRESSED_BYTES", 1500)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(IngestionError, match="Total uncompressed size exceeds cap"):
            HardenedZipExtractor.extract(content, tmpdir)

def test_per_file_size_cap(monkeypatch):
    content = create_in_memory_zip({"large_file.txt": b"a" * 2000})
    monkeypatch.setattr("gdg_yorku_submission.ingestion.MAX_PER_FILE_BYTES", 1000)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(IngestionError, match="exceeds per-file cap"):
            HardenedZipExtractor.extract(content, tmpdir)

def test_forged_header_bomb(monkeypatch):
    """Test that limits are enforced dynamically even if header declares a small file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("forged.txt", b"a" * 20000)
    
    content = buf.getvalue()
    
    original_infolist = zipfile.ZipFile.infolist
    def mock_infolist(self):
        infos = original_infolist(self)
        for i in infos:
            if i.filename == "forged.txt":
                i.file_size = 10  # Attacker lies about size
        return infos
        
    monkeypatch.setattr(zipfile.ZipFile, "infolist", mock_infolist)
    monkeypatch.setattr("gdg_yorku_submission.ingestion.MAX_PER_FILE_BYTES", 1000)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(IngestionError) as exc_info:
            HardenedZipExtractor.extract(content, tmpdir)
        
        # Python's ZipExtFile natively truncates extraction to info.file_size.
        # If the attacker declares file_size=10, the stream yields exactly 10 bytes 
        # and then raises a Bad CRC-32 error. Thus, a multi-GB bomb with a small 
        # declared size cannot physically bypass the cap to write gigabytes.
        # We assert that it either hits our cap, or safely aborts via CRC validation.
        err_msg = str(exc_info.value)
        assert "exceeds per-file cap" in err_msg or "Invalid zip archive" in err_msg

def test_skip_traversal():
    # Defer content generation so we can inject the sibling dir name
    with tempfile.TemporaryDirectory() as tmpdir:
        sibling_name = os.path.basename(tmpdir) + "_evil"
        sibling_path = os.path.join(os.path.dirname(tmpdir), sibling_name)
        os.makedirs(sibling_path, exist_ok=True)
        
        try:
            content = create_in_memory_zip({
                "../escaped.txt": b"secret",
                f"../{sibling_name}/x.txt": b"secret",
                "valid.txt": b"ok"
            })
            
            manifest = HardenedZipExtractor.extract(content, tmpdir)
            assert "../escaped.txt" in manifest.skipped_files
            assert manifest.skipped_files["../escaped.txt"].skipped_reason == "Path traversal attempt"
            
            sibling_entry = f"../{sibling_name}/x.txt"
            assert sibling_entry in manifest.skipped_files
            assert manifest.skipped_files[sibling_entry].skipped_reason == "Path traversal attempt"
            assert "valid.txt" in manifest.extracted_files
            
            # Assert nothing was written to the sibling directory
            assert len(os.listdir(sibling_path)) == 0
        finally:
            os.rmdir(sibling_path)

def test_skip_nested_archive():
    content = create_in_memory_zip({
        "inner.zip": b"PK\x03\x04",
        "valid.txt": b"ok"
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = HardenedZipExtractor.extract(content, tmpdir)
        assert "inner.zip" in manifest.skipped_files
        assert manifest.skipped_files["inner.zip"].skipped_reason == "Nested archive"

def test_skip_system_excludes_and_binaries():
    content = create_in_memory_zip({
        ".venv/lib/site-packages/x.py": b"x",
        "database.db": b"sqlite3",
        "valid.txt": b"ok"
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = HardenedZipExtractor.extract(content, tmpdir)
        assert ".venv/lib/site-packages/x.py" in manifest.skipped_files
        assert "database.db" in manifest.skipped_files
        assert "valid.txt" in manifest.extracted_files

def test_symlink_skip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        info = zipfile.ZipInfo("symlink.txt")
        info.external_attr = 0o120000 << 16  # Symlink
        z.writestr(info, "target.txt")
        z.writestr("target.txt", b"ok")
        
    content = buf.getvalue()
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = HardenedZipExtractor.extract(content, tmpdir)
        assert "symlink.txt" in manifest.skipped_files
        assert manifest.skipped_files["symlink.txt"].skipped_reason == "Symlink entry"
        assert "target.txt" in manifest.extracted_files

def test_absolute_path_skip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr("/etc/passwd", b"root:x:0:0:")
        z.writestr("C:\\Windows\\System32\\cmd.exe", b"binary")
        z.writestr("valid.txt", b"ok")
        
    content = buf.getvalue()
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = HardenedZipExtractor.extract(content, tmpdir)
        assert "/etc/passwd" in manifest.skipped_files
        assert "C:/Windows/System32/cmd.exe" in manifest.skipped_files
        assert manifest.skipped_files["C:/Windows/System32/cmd.exe"].skipped_reason == "Absolute path entry"
        assert "valid.txt" in manifest.extracted_files
