"""
Central Configuration for AI-Powered Hand Gesture Recognition System.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple
import os

# Suppress internal C++ logging noise from TensorFlow & MediaPipe
os.environ["GLOG_minloglevel"] = "3"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Paths
MODELS_DIR = BACKEND_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
BEST_MODEL_PATH = MODELS_DIR / "best_model.pkl"

DATASET_DIR = PROJECT_ROOT / "dataset"
DATASET_DIR.mkdir(parents=True, exist_ok=True)
DATASET_FILE = DATASET_DIR / "gestures.csv"

DATABASE_DIR = BACKEND_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "gesture.db"

SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# MediaPipe Task file
TASK_MODEL_PATH = PROJECT_ROOT / "hand_landmarker.task"
if not TASK_MODEL_PATH.exists():
    TASK_MODEL_PATH = BACKEND_DIR / "hand_landmarker.task"

# Auto-download official MediaPipe task model if missing in fresh container / cloud deployment
if not TASK_MODEL_PATH.exists():
    try:
        import urllib.request
        print("[Config] Downloading official MediaPipe hand_landmarker.task model...")
        model_url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        TASK_MODEL_PATH = PROJECT_ROOT / "hand_landmarker.task"
        urllib.request.urlretrieve(model_url, str(TASK_MODEL_PATH))
        print(f"[Config] Downloaded hand_landmarker.task ({TASK_MODEL_PATH.stat().st_size} bytes)")
    except Exception as e:
        print(f"[Config Warning] Could not auto-download MediaPipe task model: {e}")

# Complete Gestures Supported
GESTURES_BASIC: List[str] = [
    "Open Palm",
    "Fist",
    "Thumbs Up",
    "Thumbs Down",
    "Victory",
    "One Finger",
    "Two Fingers",
    "Three Fingers",
    "Four Fingers",
    "Five Fingers",
]

GESTURES_ADVANCED: List[str] = [
    "OK Sign",
    "Rock Sign",
    "Call Me",
    "Point Left",
    "Point Right",
    "Stop",
    "Peace",
]

ALL_GESTURES: List[str] = GESTURES_BASIC + GESTURES_ADVANCED

GESTURE_ICONS: Dict[str, str] = {
    "Open Palm": "✋",
    "Fist": "✊",
    "Thumbs Up": "👍",
    "Thumbs Down": "👎",
    "Victory": "✌️",
    "One Finger": "☝️",
    "Two Fingers": "✌️",
    "Three Fingers": "🤟",
    "Four Fingers": "🖖",
    "Five Fingers": "🖐️",
    "OK Sign": "👌",
    "Rock Sign": "🤘",
    "Call Me": "🤙",
    "Point Left": "👈",
    "Point Right": "👉",
    "Stop": "✋",
    "Peace": "✌️",
    "No Hand": "❌",
    "Unknown": "❓",
}

@dataclass
class CameraSettings:
    device_index: int = 0
    width: int = 640
    height: int = 480
    fps_limit: int = 30
    flip_horizontal: bool = True

@dataclass
class DetectionSettings:
    model_path: str = str(TASK_MODEL_PATH)
    num_hands: int = 2
    min_hand_detection_confidence: float = 0.50
    min_hand_presence_confidence: float = 0.50
    min_tracking_confidence: float = 0.50
    smoothing_factor: float = 0.70

@dataclass
class ColorPalette:
    PRIMARY: Tuple[int, int, int] = (241, 102, 99)       # Indigo (#6366F1 in BGR)
    SECONDARY: Tuple[int, int, int] = (246, 92, 139)     # Purple (#8B5CF6 in BGR)
    ACCENT: Tuple[int, int, int] = (94, 197, 34)         # Green (#22C55E in BGR)
    CYAN: Tuple[int, int, int] = (255, 235, 0)
    GOLD: Tuple[int, int, int] = (0, 215, 255)
    RED: Tuple[int, int, int] = (60, 60, 240)

camera_settings = CameraSettings()
detection_settings = DetectionSettings()
colors = ColorPalette()

# Expose AppConfig and SNAPSHOT_DIR for cross-compatibility with studio modules
SNAPSHOT_DIR = PROJECT_ROOT / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

try:
    import importlib.util
    _root_config_path = PROJECT_ROOT / "config.py"
    if _root_config_path.exists():
        spec = importlib.util.spec_from_file_location("root_config_module", str(_root_config_path))
        root_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(root_config)
        AppConfig = getattr(root_config, "AppConfig", None)
    else:
        AppConfig = None
except Exception:
    AppConfig = None
