"""
Root Shim for HandTracker.
Re-exports seamlessly from backend.hand_tracker for backwards compatibility.
"""
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from backend.hand_tracker import *
