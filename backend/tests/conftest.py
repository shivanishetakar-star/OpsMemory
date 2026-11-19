import sys
from pathlib import Path

# Ensure backend/ is importable so tests can `import classification`
# regardless of whether pytest is invoked from the repo root or backend/.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
