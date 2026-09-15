"""
Root Configuration Shim for OmniGesture AI Studio.
Aliases seamlessly to backend.config for unified settings across desktop and web.
"""
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from backend.config import (
    AppConfig,
    CameraConfig,
    TrackerConfig,
    StudioColorPalette,
    CanvasConfig,
    MouseConfig,
    CameraSettings,
    DetectionSettings,
    ColorPalette,
    camera_settings,
    detection_settings,
    colors,
    SNAPSHOT_DIR,
    SCREENSHOTS_DIR,
    TASK_MODEL_PATH,
    MODEL_PATH,
    DATASET_DIR,
    DATASET_FILE,
    MODELS_DIR,
    BEST_MODEL_PATH,
    DATABASE_DIR,
    DATABASE_PATH,
    ALL_GESTURES,
    GESTURES_BASIC,
    GESTURES_ADVANCED,
    GESTURE_ICONS,
)

PROJECT_ROOT = _ROOT
