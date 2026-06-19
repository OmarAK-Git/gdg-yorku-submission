import os
import zipfile
import io
from typing import Dict, Any, Tuple
from pathlib import Path
from gdg_yorku_submission.schemas import IngestionManifest, SkippedEntry

# Constants for caps
MAX_COMPRESSED_BYTES = 50 * 1024 * 1024       # 50MB
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024    # 500MB
MAX_FILE_COUNT = 10000                        # 10k files
MAX_PER_FILE_BYTES = 50 * 1024 * 1024         # 50MB

SYSTEM_EXCLUDES = {
    ".venv", "venv", "env", ".env_test", "node_modules", 
    "__pycache__", ".git"
}
BINARY_EXTENSIONS = {
    ".pyc", ".db", ".sqlite", ".sqlite3", ".exe", ".dll", 
    ".so", ".dylib", ".bin", ".dat", ".png", ".jpg", 
    ".jpeg", ".gif", ".ico", ".pdf"
}

class IngestionError(Exception):
    """Exception raised when an ingestion cap is exceeded."""
    pass

class HardenedZipExtractor:
    """Safely extracts a ZIP archive into a workspace, enforcing caps and skip policies."""
    
    @staticmethod
    def extract(content: bytes, dest_dir: str) -> IngestionManifest:
        """
        Extracts content to dest_dir safely.
        Returns an IngestionManifest mapping extracted paths and skipped paths.
        """
        if len(content) > MAX_COMPRESSED_BYTES:
            raise IngestionError(f"Compressed size ({len(content)} bytes) exceeds cap ({MAX_COMPRESSED_BYTES})")
            
        manifest = IngestionManifest()
        
        dest_path = Path(dest_dir).resolve()
        
        total_bytes = 0
        file_count = 0
        
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                # Do not call testzip(). It consumes unbounded CPU/memory.
                # Validations occur dynamically per file stream.
                
                for info in z.infolist():
                    if info.is_dir():
                        continue
                        
                    # 1. Skip Policy: Inner archives
                    if info.filename.lower().endswith(('.zip', '.tar', '.gz', '.tgz', '.whl', '.jar')):
                        manifest.skipped_files[info.filename] = SkippedEntry(skipped_reason="Nested archive")
                        continue
                        
                    # 2. Skip Policy: Absolute path
                    path_obj = Path(info.filename)
                    if path_obj.is_absolute() or path_obj.drive:
                        manifest.skipped_files[info.filename] = SkippedEntry(skipped_reason="Absolute path entry")
                        continue
                        
                    # 3. Skip Policy: Path Traversal
                    # Use is_relative_to for robust sibling prefix containment
                    target_path = (dest_path / info.filename).resolve()
                    try:
                        target_path.relative_to(dest_path)
                    except ValueError:
                        manifest.skipped_files[info.filename] = SkippedEntry(skipped_reason="Path traversal attempt")
                        continue
                        
                    # 4. Skip Policy: Symlinks
                    is_symlink = (info.external_attr >> 16) & 0o120000 == 0o120000
                    if is_symlink:
                        manifest.skipped_files[info.filename] = SkippedEntry(skipped_reason="Symlink entry")
                        continue
                        
                    # 5. Skip Policy: System Excludes & Binaries
                    path_parts = path_obj.parts
                    if any(part in SYSTEM_EXCLUDES for part in path_parts):
                        manifest.skipped_files[info.filename] = SkippedEntry(skipped_reason="System exclude directory")
                        continue
                        
                    ext = path_obj.suffix.lower()
                    if ext in BINARY_EXTENSIONS:
                        manifest.skipped_files[info.filename] = SkippedEntry(skipped_reason="Binary file extension")
                        continue

                    # 6. Check Caps dynamically via bounded decompression
                    file_count += 1
                    if file_count > MAX_FILE_COUNT:
                        raise IngestionError(f"Total file count exceeds cap ({MAX_FILE_COUNT})")

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    extracted_file_bytes = 0
                    try:
                        with z.open(info) as src, open(target_path, "wb") as dst:
                            while True:
                                chunk = src.read(8192)
                                if not chunk:
                                    break
                                
                                chunk_len = len(chunk)
                                extracted_file_bytes += chunk_len
                                if extracted_file_bytes > MAX_PER_FILE_BYTES:
                                    raise IngestionError(f"File {info.filename} exceeds per-file cap ({MAX_PER_FILE_BYTES})")
                                    
                                total_bytes += chunk_len
                                if total_bytes > MAX_UNCOMPRESSED_BYTES:
                                    raise IngestionError(f"Total uncompressed size exceeds cap ({MAX_UNCOMPRESSED_BYTES})")
                                    
                                dst.write(chunk)
                    except Exception:
                        # Clean up partial file on any exception (caps, IO, etc)
                        if target_path.exists():
                            target_path.unlink()
                        raise
                            
                    manifest.extracted_files.append(info.filename)
                    manifest.total_extracted_bytes = total_bytes
                    manifest.total_extracted_count = file_count
                    
        except zipfile.BadZipFile as e:
            raise IngestionError(f"Invalid zip archive: {str(e)}")
            
        return manifest
