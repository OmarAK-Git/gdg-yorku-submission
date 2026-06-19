import os
from pathlib import Path
from typing import Dict, Optional
import pathspec
from gdg_yorku_submission.schemas import CorpusFile, IngestionManifest, ExposureStatus, IngestStatus

def load_root_gitignore(workspace_dir: str) -> pathspec.PathSpec:
    """
    Loads and parses the root .gitignore file from workspace_dir.
    Returns a pathspec.PathSpec object.
    """
    gitignore_path = Path(workspace_dir) / ".gitignore"
    if gitignore_path.exists() and gitignore_path.is_file():
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            return pathspec.PathSpec.from_lines("gitignore", lines)
        except Exception:
            pass
    return pathspec.PathSpec.from_lines("gitignore", [])

def classify_exposure(
    rel_path: str,
    is_skipped: bool,
    spec: pathspec.PathSpec
) -> ExposureStatus:
    """
    Classifies a file's exposure status into the three-value spec triad.
    """
    normalized_path = rel_path.replace("\\", "/")
    if is_skipped:
        return "excluded_by_system"
    
    if spec.match_file(normalized_path):
        return "ignored_by_root_gitignore"
    
    return "prompt_exposed"

def build_corpus(workspace_dir: str, manifest: IngestionManifest) -> Dict[str, CorpusFile]:
    """
    Builds the corpus of CorpusFile models from the extracted files in workspace_dir.
    """
    spec = load_root_gitignore(workspace_dir)
    corpus = {}
    workspace_path = Path(workspace_dir).resolve()

    # Process all extracted files
    for rel_path in manifest.extracted_files:
        normalized_path = rel_path.replace("\\", "/")
        file_path = workspace_path / rel_path

        original_text = ""
        read_failed = False
        try:
            if file_path.exists() and file_path.is_file():
                # errors="replace" ensures tolerant decoding for secret scanning (N2)
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    original_text = f.read()
            else:
                read_failed = True
        except Exception:
            read_failed = True

        if read_failed:
            exposure = "excluded_by_system"
            ingest_status = "read_failure"
            original_line_count = 0
            line_map = {}
        else:
            exposure = classify_exposure(normalized_path, False, spec)
            ingest_status = "success"
            lines = original_text.splitlines()
            original_line_count = len(lines)
            line_map = {i: i for i in range(1, original_line_count + 1)}

        evidence_ref = f"file:{normalized_path}"

        if normalized_path in corpus:
            raise ValueError(f"Duplicate path in corpus: {normalized_path}")

        corpus[normalized_path] = CorpusFile(
            normalized_path=normalized_path,
            original_text=original_text,
            redacted_text=original_text,  # Initially identical
            original_line_count=original_line_count,
            redacted_to_original_line_map=line_map,
            evidence_ref=evidence_ref,
            exposure_status=exposure,
            ingest_status=ingest_status
        )

    # Process all skipped files
    for rel_path, entry in manifest.skipped_files.items():
        normalized_path = rel_path.replace("\\", "/")
        exposure = classify_exposure(normalized_path, True, spec)
        evidence_ref = f"file:{normalized_path}"

        if entry.skipped_reason in ("System exclude directory", "Binary file extension"):
            ingest_status = "success"
        else:
            ingest_status = "security_skip"

        if normalized_path in corpus:
            raise ValueError(f"Duplicate path in corpus: {normalized_path}")

        corpus[normalized_path] = CorpusFile(
            normalized_path=normalized_path,
            original_text="",
            redacted_text="",
            original_line_count=0,
            redacted_to_original_line_map={},
            evidence_ref=evidence_ref,
            exposure_status=exposure,
            ingest_status=ingest_status
        )

    # Conservation assertion (N4)
    if len(corpus) != len(manifest.extracted_files) + len(manifest.skipped_files):
        raise AssertionError("Conservation check failed: corpus count does not equal extracted + skipped count")

    return corpus

def get_prompt_corpus(corpus: Dict[str, CorpusFile]) -> Dict[str, CorpusFile]:
    """
    Returns only the files that are prompt_exposed.
    """
    return {path: f for path, f in corpus.items() if f.exposure_status == "prompt_exposed"}
