import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root directory to sys.path so tests can import from scripts/ or src/
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Load .env variables so integration/live tests can access credentials
load_dotenv(root_dir / ".env")

os.environ["USE_FAKE_LLM"] = "true"

import pytest
from gdg_yorku_submission.orchestrator import AdkOrchestrator

@pytest.fixture(autouse=True)
def clear_adk_store():
    AdkOrchestrator.clear_shared_store()
    yield
    AdkOrchestrator.clear_shared_store()
