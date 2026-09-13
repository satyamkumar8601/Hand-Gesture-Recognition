"""
Configuration settings for OmniGesture AI Studio.
Performance-tuned for low latency, smooth tracking, and responsiveness.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple
import os

os.environ["GLOG_minloglevel"] = "3"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "hand_landmarker.task"
SNAPSHOT_DIR = PROJECT_ROOT / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

@dataclass
class CameraConfig:
    device_index: int = 0
    width: int = 640       # 640x480 for 3x lower latency & high responsiveness
    height: int = 480
    target_fps: int = 30
    flip_horizontal: bool = True

@dataclass
class TrackerConfig:
    model_path: str = str(MODEL_PATH)
    num_hands: int = 2
    min_hand_detection_confidence: float = 0.50
    min_hand_presence_confidence: float = 0.50
    min_tracking_confidence: float = 0.50
    smoothing_factor: float = 0.75  # Higher alpha = instant responsiveness (no sluggish trailing)
    inference_width: int = 480      # Downscaled size fed to MediaPipe for rapid inference
    inference_height: int = 360

@dataclass
class ColorPalette:
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
    colors: ColorPalette = ColorPalette()
    canvas: CanvasConfig = CanvasConfig()
    mouse: MouseConfig = MouseConfig()
