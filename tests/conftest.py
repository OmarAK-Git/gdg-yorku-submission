import sys
from pathlib import Path

# Add the project root directory to sys.path so tests can import from scripts/ or src/
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from gdg_yorku_submission.orchestrator import AdkOrchestrator

@pytest.fixture(autouse=True)
def clear_adk_store():
    AdkOrchestrator.clear_shared_store()
    yield
    AdkOrchestrator.clear_shared_store()
