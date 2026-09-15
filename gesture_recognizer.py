"""
Root Shim for GestureRecognizer.
Re-exports seamlessly from backend.gesture_recognizer for backwards compatibility.
"""
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from backend.gesture_recognizer import *
