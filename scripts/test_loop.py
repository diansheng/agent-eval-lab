import json
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from app.config import load_settings
from app.agent import review_pull_request

settings = load_settings()
try:
    result = review_pull_request(settings, "openclaw", "openclaw", 93249)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
    if hasattr(e, "trace"):
        print(json.dumps(e.trace, indent=2))
