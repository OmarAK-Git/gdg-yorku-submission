# Verification Plan for Task 5

## Unit Tests
- Create `tests/test_ingestion.py`.
- Ensure coverage of caps (count, uncompressed size).
- Ensure coverage of skipped entries (traversal, absolute path, nested zip).
- Run `pytest tests/test_ingestion.py`.

## API Tests
- Update `tests/test_api_skeleton.py` to upload a valid zip and verify that `corpus_summary` is populated.

## Commands
```bash
python -m pytest tests/test_ingestion.py -v
python -m pytest tests/test_api_skeleton.py -v
```
