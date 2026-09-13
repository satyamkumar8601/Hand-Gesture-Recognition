"""
Prediction Pipeline & Overlay Engine.
Orchestrates Camera -> Detection -> Recognition -> Telemetry -> Database Logging.
Supports 4 Integrated Studio Modes:
  1: HUD & Gesture Analytics
  2: Air Canvas (Virtual Drawing & Whiteboard)
  3: Virtual Mouse (Cursor & Pinch Clicks)
  4: Biometrics & Rehabilitation Tracker
"""
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import sys
import time
import cv2
import numpy as np

# Ensure project root and backend are accessible
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from backend.config import colors
    from backend.services.camera_service import CameraService
    from backend.services.hand_detector import HandDetector, HandLandmarksData
    from backend.services.gesture_detector import GestureDetector, GestureResult
    from backend.database.db import log_gesture
except ImportError:
    from config import colors
    from services.camera_service import CameraService
    from services.hand_detector import HandDetector, HandLandmarksData
    from services.gesture_detector import GestureDetector, GestureResult
    from database.db import log_gesture

# Import interactive studio modules
try:
    from air_canvas import AirCanvas
    from virtual_mouse import VirtualMouse
    from rehab_tracker import RehabTracker
    from hud_renderer import HUDRenderer
    from hand_tracker import HandData
    MODULES_AVAILABLE = True
except Exception as e:
    print(f"[PredictionService Warning] Interactive modules import error: {e}")
    MODULES_AVAILABLE = False


def to_hand_data(h: HandLandmarksData) -> Any:
    """Convert HandLandmarksData to HandData format for interactive modules."""
    if not MODULES_AVAILABLE:
        return h
    wrist_px = h.landmarks_pixel[0]
    middle_mcp_px = h.landmarks_pixel[9]
    palm_center = (int((wrist_px[0] + middle_mcp_px[0]) // 2), int((wrist_px[1] + middle_mcp_px[1]) // 2))
    return HandData(
        handedness=h.handedness,
        handedness_score=0.99,
        landmarks_norm=h.raw_normalized,
        landmarks_pixel=h.landmarks_pixel,
        bbox=h.bbox,
        hand_size=h.hand_scale,
        palm_center=palm_center,
    )


class PredictionService:
    _instance: Optional["PredictionService"] = None

    def __init__(self):
        self.camera_service = CameraService.get_instance()
        self.hand_detector = HandDetector()
        self.gesture_detector = GestureDetector()

        self.width = self.camera_service.width
        self.height = self.camera_service.height

        self.prev_time = time.time()
        self.fps_smooth = 30.0

        self.last_logged_gesture: Optional[str] = None
        self.last_log_time = 0.0

        # Frame ID caching for zero redundant inferences
        self.last_frame_id = -1
        self.cached_display_frame: Optional[np.ndarray] = None

        # Mode State (1: HUD, 2: Canvas, 3: Mouse, 4: Rehab)
        self.mode = 1
        self.mode_names = {
            1: "HUD Analytics",
            2: "Air Canvas",
            3: "Virtual Mouse",
            4: "Biometrics & Rehab",
        }

        # Initialize interactive studio modules
        if MODULES_AVAILABLE:
            self.air_canvas = AirCanvas(width=self.width, height=self.height)
            self.virtual_mouse = VirtualMouse(camera_w=self.width, camera_h=self.height)
            self.hud_renderer = HUDRenderer(width=self.width, height=self.height)
            self.rehab_tracker = RehabTracker(width=self.width, height=self.height)
        else:
            self.air_canvas = None
            self.virtual_mouse = None
            self.hud_renderer = None
            self.rehab_tracker = None

        # Latest live telemetry state for Web API
        self.latest_state: Dict[str, Any] = {
            "fps": 0.0,
            "hand_detected": False,
            "hands_count": 0,
            "primary_gesture": "No Hand",
            "confidence": 0.0,
            "is_ml": False,
            "icon": "❌",
            "finger_states": {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False},
            "probabilities": {},
            "camera_active": False,
            "mode": 1,
            "mode_name": "HUD Analytics",
            "mouse_enabled": False,
            "canvas_color": "Cyan",
            "whiteboard_mode": False,
            "rehab_grip_closure": 0.0,
            "rehab_extended_fingers": 0,
        }

    @classmethod
    def get_instance(cls) -> "PredictionService":
        if cls._instance is None:
            cls._instance = PredictionService()
        return cls._instance

    # Mode Control
    def set_mode(self, mode_id: int) -> bool:
        if mode_id in [1, 2, 3, 4]:
            self.mode = mode_id
            if self.mode == 3 and self.virtual_mouse:
                self.virtual_mouse.enabled = True
            if self.hud_renderer:
                self.hud_renderer.notify(f"Mode: {self.mode_names.get(mode_id, 'Unknown')}")
            return True
        return False

    def get_mode(self) -> int:
        return self.mode

    # Air Canvas Actions
    def clear_canvas(self) -> bool:
        if self.air_canvas:
            self.air_canvas.clear()
            if self.hud_renderer:
                self.hud_renderer.notify("Canvas Cleared")
            return True
        return False

    def undo_canvas(self) -> bool:
        if self.air_canvas:
            res = self.air_canvas.undo()
            if res and self.hud_renderer:
                self.hud_renderer.notify("Stroke Undone")
            return res
        return False

    def set_canvas_color(self, color_name: str) -> bool:
        if not self.air_canvas:
            return False
        color_map = {
            "Cyan": ((255, 235, 0), False),
            "Neon Pink": ((230, 40, 255), False),
            "Pink": ((230, 40, 255), False),
            "Green": ((80, 255, 120), False),
            "Emerald": ((80, 255, 120), False),
            "Yellow": ((0, 215, 255), False),
            "Gold": ((0, 215, 255), False),
            "Red": ((60, 60, 255), False),
            "Purple": ((255, 100, 180), False),
            "White": ((255, 255, 255), False),
            "Eraser": ((0, 0, 0), True),
        }
        if color_name in color_map:
            bgr, is_eraser = color_map[color_name]
            self.air_canvas.current_color = bgr
            self.air_canvas.current_color_name = color_name
            self.air_canvas.is_eraser = is_eraser
            if self.hud_renderer:
                self.hud_renderer.notify(f"Color: {color_name}")
            return True
        return False

    def toggle_whiteboard(self) -> bool:
        if self.air_canvas:
            self.air_canvas.whiteboard_mode = not self.air_canvas.whiteboard_mode
            if self.hud_renderer:
                self.hud_renderer.notify("Whiteboard ON" if self.air_canvas.whiteboard_mode else "Camera ON")
            return self.air_canvas.whiteboard_mode
        return False

    def set_brush_size(self, size: int) -> bool:
        if self.air_canvas:
            self.air_canvas.brush_size = max(2, min(50, size))
            return True
        return False

    # Virtual Mouse Actions
    def toggle_mouse(self) -> bool:
        if self.virtual_mouse:
            state = self.virtual_mouse.toggle()
            if self.hud_renderer:
                self.hud_renderer.notify("Mouse ACTIVE" if state else "Mouse PAUSED")
            return state
        return False

    def get_rehab_metrics(self) -> Dict[str, Any]:
        return {
            "grip_closure": self.latest_state.get("rehab_grip_closure", 0.0),
            "extended_fingers": self.latest_state.get("rehab_extended_fingers", 0),
            "hands_count": self.latest_state.get("hands_count", 0),
            "primary_gesture": self.latest_state.get("primary_gesture", "No Hand"),
        }

    def process_live_frame(self, draw_landmarks: bool = True, draw_hud: bool = True) -> Tuple[bool, Optional[np.ndarray], Dict[str, Any]]:
        """
        Grab freshest frame, run tracking, annotate according to active mode, and return frame & telemetry.
        Leverages frame_id caching to skip redundant inferences when called faster than webcam FPS.
        """
        ret, frame, frame_id = self.camera_service.read_frame_with_id()
        if not ret or frame is None:
            self.latest_state["camera_active"] = False
            return False, None, self.latest_state

        if frame_id == self.last_frame_id and self.cached_display_frame is not None:
            return True, self.cached_display_frame.copy(), self.latest_state

        # Horizontal flip for intuitive mirror interaction
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        # Adapt module sizes if resolution changed
        if self.width != w or self.height != h:
            self.width, self.height = w, h
            if MODULES_AVAILABLE:
                self.air_canvas = AirCanvas(width=w, height=h)
                self.virtual_mouse = VirtualMouse(camera_w=w, camera_h=h)
                self.hud_renderer = HUDRenderer(width=w, height=h)
                self.rehab_tracker = RehabTracker(width=w, height=h)

        # FPS calculation
        now = time.time()
        dt = now - self.prev_time
        self.prev_time = now
        if dt > 0:
            self.fps_smooth = 0.9 * self.fps_smooth + 0.1 * (1.0 / dt)
        fps_val = round(self.fps_smooth, 1)

        # Process 3D Hand Landmarks
        hands = self.hand_detector.process_frame(frame)
        gesture_results: List[GestureResult] = [self.gesture_detector.recognize(h) for h in hands]
        converted_hands = [to_hand_data(h) for h in hands]

        display_frame = frame.copy()
        grip_closure_val = 0.0
        total_extended = 0

        if hands:
            primary_hand = hands[0]
            primary_res = gesture_results[0]
            total_extended = sum(g.finger_states.count_extended() for g in gesture_results)

            if MODULES_AVAILABLE and self.rehab_tracker:
                grip_closure_val = self.rehab_tracker.compute_grip_closure(converted_hands[0])

            primary_idx = 0
            for idx, h in enumerate(hands):
                if h.handedness == "Right":
                    primary_idx = idx
                    break

            # Debounced database logging
            if primary_res.name not in ["No Hand", "Unknown"]:
                if primary_res.name != self.last_logged_gesture or (now - self.last_log_time > 2.5):
                    log_gesture(primary_res.name, primary_res.confidence, primary_res.handedness)
                    self.last_logged_gesture = primary_res.name
                    self.last_log_time = now

            # ==============================================================
            # MODE-SPECIFIC RENDERING
            # ==============================================================
            if self.mode == 2 and MODULES_AVAILABLE and self.air_canvas:
                # Mode 2: Air Canvas
                status = self.air_canvas.update(converted_hands[primary_idx], primary_res)
                if status and self.hud_renderer:
                    self.hud_renderer.notify(status, duration=1.0)

                display_frame = self.air_canvas.render_composite(frame)
                if draw_landmarks and self.hud_renderer:
                    accent = self.air_canvas.current_color if not self.air_canvas.is_eraser else (200, 200, 200)
                    display_frame = self.hud_renderer.draw_skeleton(display_frame, converted_hands[primary_idx], accent)

            elif self.mode == 3 and MODULES_AVAILABLE and self.virtual_mouse:
                # Mode 3: Virtual Mouse
                cv2.rectangle(
                    display_frame,
                    (self.virtual_mouse.box_x1, self.virtual_mouse.box_y1),
                    (self.virtual_mouse.box_x2, self.virtual_mouse.box_y2),
                    (60, 60, 80),
                    1,
                    cv2.LINE_AA,
                )
                m_status = "MOUSE ACTIVE" if self.virtual_mouse.enabled else "MOUSE PAUSED (Click Toggle)"
                cv2.putText(
                    display_frame,
                    m_status,
                    (self.virtual_mouse.box_x1 + 10, self.virtual_mouse.box_y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (80, 255, 120) if self.virtual_mouse.enabled else (140, 140, 140),
                    1,
                    cv2.LINE_AA,
                )
                status = self.virtual_mouse.update(converted_hands[primary_idx], primary_res)
                if status and self.hud_renderer:
                    self.hud_renderer.notify(status, duration=0.8)

                if draw_landmarks and self.hud_renderer:
                    for ch in converted_hands:
                        display_frame = self.hud_renderer.draw_skeleton(display_frame, ch, colors.CYAN)

            elif self.mode == 4 and MODULES_AVAILABLE and self.rehab_tracker:
                # Mode 4: Biometrics & Rehab
                if draw_landmarks and self.hud_renderer:
                    for ch in converted_hands:
                        accent = colors.CYAN if ch.handedness == "Right" else (230, 40, 255)
                        display_frame = self.hud_renderer.draw_skeleton(display_frame, ch, accent)
                display_frame = self.rehab_tracker.draw_rehab_dashboard(display_frame, converted_hands, gesture_results)

            else:
                # Mode 1: HUD Analytics (Default)
                if draw_landmarks:
                    if MODULES_AVAILABLE and self.hud_renderer:
                        for idx, (ch, g) in enumerate(zip(converted_hands, gesture_results)):
                            accent = colors.CYAN if ch.handedness == "Right" else (230, 40, 255)
                            display_frame = self.hud_renderer.draw_skeleton(display_frame, ch, accent)
                            display_frame = self.hud_renderer.draw_bounding_box(display_frame, ch, g.name)
                            display_frame = self.hud_renderer.draw_gesture_card(display_frame, ch, g, slot_idx=idx)
                    else:
                        display_frame = self.hand_detector.draw_landmarks(display_frame, hands)

                if draw_hud:
                    display_frame = self._render_hud_overlay(display_frame, primary_res, fps_val)

            # Update Telemetry State
            self.latest_state = {
                "fps": fps_val,
                "hand_detected": True,
                "hands_count": len(hands),
                "primary_gesture": primary_res.name,
                "confidence": round(primary_res.confidence * 100, 1),
                "is_ml": primary_res.is_ml,
                "icon": primary_res.icon,
                "finger_states": primary_res.finger_states.as_dict(),
                "probabilities": primary_res.probabilities,
                "camera_active": True,
                "mode": self.mode,
                "mode_name": self.mode_names.get(self.mode, "HUD Analytics"),
                "mouse_enabled": self.virtual_mouse.enabled if self.virtual_mouse else False,
                "canvas_color": self.air_canvas.current_color_name if self.air_canvas else "Cyan",
                "whiteboard_mode": self.air_canvas.whiteboard_mode if self.air_canvas else False,
                "rehab_grip_closure": round(grip_closure_val, 1),
                "rehab_extended_fingers": total_extended,
            }

        else:
            self.last_logged_gesture = None
            if self.mode == 2 and MODULES_AVAILABLE and self.air_canvas and self.air_canvas.whiteboard_mode:
                display_frame = self.air_canvas.render_composite(frame)

            self.latest_state = {
                "fps": fps_val,
                "hand_detected": False,
                "hands_count": 0,
                "primary_gesture": "No Hand",
                "confidence": 0.0,
                "is_ml": False,
                "icon": "❌",
                "finger_states": {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False},
                "probabilities": {},
                "camera_active": True,
                "mode": self.mode,
                "mode_name": self.mode_names.get(self.mode, "HUD Analytics"),
                "mouse_enabled": self.virtual_mouse.enabled if self.virtual_mouse else False,
                "canvas_color": self.air_canvas.current_color_name if self.air_canvas else "Cyan",
                "whiteboard_mode": self.air_canvas.whiteboard_mode if self.air_canvas else False,
                "rehab_grip_closure": 0.0,
                "rehab_extended_fingers": 0,
            }

            if draw_hud:
                # Top telemetry badge
                cv2.rectangle(display_frame, (10, 10), (160, 45), (20, 22, 28), -1)
                cv2.rectangle(display_frame, (10, 10), (160, 45), (60, 60, 80), 1)
                cv2.putText(display_frame, f"FPS: {fps_val}", (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.55, colors.ACCENT, 1, cv2.LINE_AA)

        # Top Mode Banner Badge on all frames
        mode_badge = f"MODE: {self.mode_names.get(self.mode, 'HUD').upper()}"
        cv2.rectangle(display_frame, (w - 220, 10), (w - 10, 45), (20, 22, 28), -1)
        cv2.rectangle(display_frame, (w - 220, 10), (w - 10, 45), (60, 60, 80), 1)
        cv2.putText(display_frame, mode_badge, (w - 205, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.48, colors.CYAN, 1, cv2.LINE_AA)

        # Cache annotated frame for subsequent instant queries
        self.last_frame_id = frame_id
        self.cached_display_frame = display_frame

        return True, display_frame, self.latest_state

    def _render_hud_overlay(self, frame: np.ndarray, res: GestureResult, fps: float) -> np.ndarray:
        """Render cyberpunk neon telemetry card onto camera feed."""
        h, w = frame.shape[:2]

        # Top-left FPS badge
        cv2.rectangle(frame, (10, 10), (170, 45), (20, 22, 28), -1)
        cv2.rectangle(frame, (10, 10), (170, 45), (60, 60, 80), 1)
        cv2.putText(frame, f"FPS: {fps}", (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.55, colors.ACCENT, 1, cv2.LINE_AA)

        # Bottom banner card with glassmorphic style
        card_h = 75
        y1 = h - card_h - 15
        y2 = h - 15
        x1 = 15
        x2 = min(360, w - 15)

        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (18, 20, 28), -1)
        frame = cv2.addWeighted(overlay, 0.82, frame, 0.18, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), colors.PRIMARY, 1, cv2.LINE_AA)

        # Gesture Name & Engine Type
        cv2.putText(frame, f"{res.name.upper()}", (x1 + 14, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)
        engine_str = "AI MODEL (ML)" if res.is_ml else "HYBRID (RULE)"
        cv2.putText(frame, engine_str, (x1 + 14, y1 + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.38, colors.CYAN if res.is_ml else colors.GOLD, 1, cv2.LINE_AA)

        # Confidence Bar
        bar_x = x1 + 14
        bar_y = y1 + 56
        bar_w = x2 - x1 - 28
        bar_h = 6
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (45, 45, 55), -1)
        fill_w = int(bar_w * res.confidence)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), colors.ACCENT, -1)

        # Confidence text readout
        conf_str = f"{int(res.confidence * 100)}%"
        cv2.putText(frame, conf_str, (x2 - 50, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.60, colors.ACCENT, 2, cv2.LINE_AA)

        return frame
