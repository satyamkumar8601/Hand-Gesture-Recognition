"""
Root Shim for VirtualMouse.
Re-exports seamlessly from backend.virtual_mouse for backwards compatibility.
"""
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from backend.virtual_mouse import *
