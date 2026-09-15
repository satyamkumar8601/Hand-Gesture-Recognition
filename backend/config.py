"""
Central Configuration for AI-Powered Hand Gesture Recognition System.
Self-contained configuration for local development and cloud (Render) deployment.
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

# Paths (Anchor primarily to BACKEND_DIR for cloud autonomy, fallback to PROJECT_ROOT)
MODELS_DIR = BACKEND_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
BEST_MODEL_PATH = MODELS_DIR / "best_model.pkl"

DATASET_DIR = BACKEND_DIR / "dataset"
if not (DATASET_DIR / "gestures.csv").exists() and (PROJECT_ROOT / "dataset" / "gestures.csv").exists():
    DATASET_DIR = PROJECT_ROOT / "dataset"
DATASET_DIR.mkdir(parents=True, exist_ok=True)
DATASET_FILE = DATASET_DIR / "gestures.csv"

DATABASE_DIR = BACKEND_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "gesture.db"

SCREENSHOTS_DIR = BACKEND_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

SNAPSHOT_DIR = BACKEND_DIR / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# MediaPipe Task file
TASK_MODEL_PATH = BACKEND_DIR / "hand_landmarker.task"
if not TASK_MODEL_PATH.exists() and (PROJECT_ROOT / "hand_landmarker.task").exists():
    TASK_MODEL_PATH = PROJECT_ROOT / "hand_landmarker.task"

# Auto-download official MediaPipe task model if missing in fresh container / cloud deployment
if not TASK_MODEL_PATH.exists():
    try:
        import urllib.request
        print("[Config] Downloading official MediaPipe hand_landmarker.task model...")
        model_url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        TASK_MODEL_PATH = BACKEND_DIR / "hand_landmarker.task"
        urllib.request.urlretrieve(model_url, str(TASK_MODEL_PATH))
        print(f"[Config] Downloaded hand_landmarker.task ({TASK_MODEL_PATH.stat().st_size} bytes)")
    except Exception as e:
        print(f"[Config Warning] Could not auto-download MediaPipe task model: {e}")

MODEL_PATH = TASK_MODEL_PATH

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
    min_hand_detection_confidence: float = 0.35
    min_hand_presence_confidence: float = 0.35
    min_tracking_confidence: float = 0.35
    smoothing_factor: float = 0.65

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

# =====================================================================
# Full AppConfig Suite (for interactive studio & desktop modules)
# =====================================================================
@dataclass
class CameraConfig:
    device_index: int = 0
    width: int = 640       # 640x480 for 3x lower latency & high responsiveness
    height: int = 480
    target_fps: int = 30
    flip_horizontal: bool = True

@dataclass
class TrackerConfig:
    model_path: str = str(TASK_MODEL_PATH)
    num_hands: int = 2
    min_hand_detection_confidence: float = 0.50
    min_hand_presence_confidence: float = 0.50
    min_tracking_confidence: float = 0.50
    smoothing_factor: float = 0.75  # Higher alpha = instant responsiveness
    inference_width: int = 480      # Downscaled size fed to MediaPipe for rapid inference
    inference_height: int = 360

@dataclass
class StudioColorPalette:
    CYAN: Tuple[int, int, int] = (255, 235, 0)
    NEON_PINK: Tuple[int, int, int] = (230, 40, 255)
    EMERALD_GREEN: Tuple[int, int, int] = (80, 255, 120)
    GOLD_YELLOW: Tuple[int, int, int] = (0, 215, 255)
    CORAL_RED: Tuple[int, int, int] = (60, 60, 255)
    PURPLE: Tuple[int, int, int] = (255, 100, 180)
    WHITE: Tuple[int, int, int] = (255, 255, 255)
    DARK_BG: Tuple[int, int, int] = (25, 22, 20)
    HUD_ACCENT: Tuple[int, int, int] = (255, 191, 0)

    PALETTE_OPTIONS: List[Tuple[str, Tuple[int, int, int]]] = field(default_factory=lambda: [
        ("Cyan", (255, 235, 0)),
        ("Neon Pink", (230, 40, 255)),
        ("Green", (80, 255, 120)),
        ("Yellow", (0, 215, 255)),
        ("Red", (60, 60, 255)),
        ("Purple", (255, 100, 180)),
        ("White", (255, 255, 255)),
        ("Eraser", (0, 0, 0)),
    ])

@dataclass
class CanvasConfig:
    default_brush_size: int = 5
    eraser_size: int = 30
    min_brush_size: int = 2
    max_brush_size: int = 30
    palette_height: int = 65
    clear_gesture_cooldown: float = 1.0
    smoothing_window: int = 2

@dataclass
class MouseConfig:
    smoothing: float = 0.75  # 0.75 = snappy cursor following
    click_threshold_ratio: float = 0.05
    double_click_interval: float = 0.35
    scroll_speed: int = 25
    edge_margin_x: float = 0.10
    edge_margin_y: float = 0.10

class AppConfig:
    camera: CameraConfig = CameraConfig()
    tracker: TrackerConfig = TrackerConfig()
    colors: StudioColorPalette = StudioColorPalette()
    canvas: CanvasConfig = CanvasConfig()
    mouse: MouseConfig = MouseConfig()
