import sys
from pathlib import Path

# Add the project root directory to sys.path so tests can import from scripts/ or src/
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
