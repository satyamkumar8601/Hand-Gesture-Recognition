"""
Air Canvas module for virtual finger painting and whiteboard sketching.
Supports multi-color palette, brush size adjustment, smoothing, eraser, and saving.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

try:
    from backend.config import AppConfig, SNAPSHOT_DIR
    from backend.hand_tracker import HandData, INDEX_TIP, THUMB_TIP
    from backend.gesture_recognizer import GestureResult
except ImportError:
    from config import AppConfig, SNAPSHOT_DIR
    from hand_tracker import HandData, INDEX_TIP, THUMB_TIP
    from gesture_recognizer import GestureResult


@dataclass
class DrawPoint:
    x: int
    y: int
    color: Tuple[int, int, int]
    radius: int


@dataclass
class PaletteItem:
    name: str
    color: Tuple[int, int, int]
    rect: Tuple[int, int, int, int]  # x1, y1, x2, y2


class AirCanvas:
    """Virtual air canvas driven by index fingertip tracking."""

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.canvas = np.zeros((height, width, 3), dtype=np.uint8)
        self.stroke_history: List[np.ndarray] = []  # Snapshots for undo
        self.max_history = 10

        # Drawing state
        self.current_color = AppConfig.colors.CYAN
        self.current_color_name = "Cyan"
        self.brush_size = AppConfig.canvas.default_brush_size
        self.prev_point: Optional[Tuple[int, int]] = None
        self.is_eraser = False
        self.whiteboard_mode = False  # False = Overlay on camera, True = Pure whiteboard

        # Palette buttons layout
        self.palette_items: List[PaletteItem] = []
        self._init_palette()

    def _init_palette(self):
        self.palette_items.clear()
        colors = AppConfig.colors.PALETTE_OPTIONS
        num_items = len(colors) + 2  # plus Clear and Undo
        item_w = self.width // num_items
        h = AppConfig.canvas.palette_height

        for idx, (name, bgr) in enumerate(colors):
            x1 = idx * item_w
            x2 = (idx + 1) * item_w
            self.palette_items.append(PaletteItem(name=name, color=bgr, rect=(x1, 0, x2, h)))

        # Add Undo button
        undo_x1 = len(colors) * item_w
        undo_x2 = undo_x1 + item_w
        self.palette_items.append(PaletteItem(name="Undo", color=(100, 100, 100), rect=(undo_x1, 0, undo_x2, h)))

        # Add Clear button
        clear_x1 = (len(colors) + 1) * item_w
        clear_x2 = self.width
        self.palette_items.append(PaletteItem(name="Clear All", color=(40, 40, 40), rect=(clear_x1, 0, clear_x2, h)))

    def save_undo_state(self):
        if len(self.stroke_history) >= self.max_history:
            self.stroke_history.pop(0)
        self.stroke_history.append(self.canvas.copy())

    def undo(self):
        if self.stroke_history:
            self.canvas = self.stroke_history.pop()
            self.prev_point = None
            return True
        return False

    def clear(self):
        self.save_undo_state()
        self.canvas.fill(0)
        self.prev_point = None

    def check_palette_selection(self, tip_x: int, tip_y: int) -> Optional[str]:
        """Check if index finger is hovering over a palette item."""
        if tip_y > AppConfig.canvas.palette_height:
            return None

        for item in self.palette_items:
            x1, y1, x2, y2 = item.rect
            if x1 <= tip_x <= x2 and y1 <= tip_y <= y2:
                if item.name == "Clear All":
                    self.clear()
                    return "Cleared Canvas"
                elif item.name == "Undo":
                    self.undo()
                    return "Undone Stroke"
                elif item.name == "Eraser":
                    self.is_eraser = True
                    self.current_color = (0, 0, 0)
                    self.current_color_name = "Eraser"
                    return "Selected Eraser"
                else:
                    self.is_eraser = False
                    self.current_color = item.color
                    self.current_color_name = item.name
                    return f"Selected {item.name}"
        return None

    def update(self, hand: HandData, gesture: GestureResult) -> Optional[str]:
        """
        Update canvas state based on detected hand position and gesture.
        """
        tip_x, tip_y = hand.landmarks_pixel[INDEX_TIP]
        finger_states = gesture.finger_states
        action_status: Optional[str] = None

        # Check if in palette zone
        if tip_y <= AppConfig.canvas.palette_height:
            action_status = self.check_palette_selection(tip_x, tip_y)
            self.prev_point = None
            return action_status

        # 1. SELECTION / HOVER MODE: Index & Middle both extended
        if finger_states.index and finger_states.middle and not finger_states.ring and not finger_states.pinky:
            self.prev_point = None
            # Dynamic brush size adjustment via index-thumb pinch distance
            if gesture.pinch_distance_ratio > 0.05:
                # Map pinch ratio [0.08, 0.45] to brush size [min_brush_size, max_brush_size]
                clamped_ratio = np.clip(gesture.pinch_distance_ratio, 0.08, 0.45)
                norm_val = (clamped_ratio - 0.08) / (0.45 - 0.08)
                new_size = int(AppConfig.canvas.min_brush_size + norm_val * (AppConfig.canvas.max_brush_size - AppConfig.canvas.min_brush_size))
                self.brush_size = new_size

        # 2. DRAWING MODE: Only Index finger is extended (or Pointing / Writing)
        elif finger_states.index and not finger_states.middle and not finger_states.ring and not finger_states.pinky:
            current_point = (int(tip_x), int(tip_y))

            if self.prev_point is None:
                self.save_undo_state()
                self.prev_point = current_point

            draw_radius = AppConfig.canvas.eraser_size if self.is_eraser else self.brush_size
            draw_color = (0, 0, 0) if self.is_eraser else self.current_color

            # Draw smooth line between consecutive points
            cv2.line(self.canvas, self.prev_point, current_point, draw_color, draw_radius * 2, cv2.LINE_AA)
            cv2.circle(self.canvas, current_point, draw_radius, draw_color, -1, cv2.LINE_AA)

            self.prev_point = current_point

        else:
            self.prev_point = None

        return action_status

    def draw_palette_ui(self, frame: np.ndarray) -> np.ndarray:
        """Render the top interactive color palette overlay."""
        h_bar = min(AppConfig.canvas.palette_height, frame.shape[0])
        sub = frame[0:h_bar, 0:self.width]
        overlay = sub.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, h_bar), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.85, sub, 0.15, 0, dst=sub)

        for item in self.palette_items:
            x1, y1, x2, y2 = item.rect
            pad = 6

            if item.name == self.current_color_name:
                # Highlight active selection
                cv2.rectangle(frame, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), (255, 255, 255), 2)

            if item.name in ["Clear All", "Undo"]:
                cv2.rectangle(frame, (x1 + pad, y1 + pad), (x2 - pad, y2 - pad), item.color, -1, cv2.LINE_AA)
                cv2.putText(
                    frame,
                    item.name,
                    (x1 + 14, y1 + h_bar // 2 + 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
            elif item.name == "Eraser":
                cv2.rectangle(frame, (x1 + pad, y1 + pad), (x2 - pad, y2 - pad), (50, 50, 60), -1, cv2.LINE_AA)
                cv2.putText(
                    frame,
                    "Eraser",
                    (x1 + 14, y1 + h_bar // 2 + 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (220, 220, 220),
                    1,
                    cv2.LINE_AA,
                )
            else:
                cv2.rectangle(frame, (x1 + pad, y1 + pad), (x2 - pad, y2 - pad), item.color, -1, cv2.LINE_AA)
                cv2.putText(
                    frame,
                    item.name,
                    (x1 + 10, y2 - 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (20, 20, 20) if np.mean(item.color) > 150 else (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

        # Draw divider line
        cv2.line(frame, (0, h_bar), (self.width, h_bar), (70, 70, 90), 2)
        return frame

    def render_composite(self, frame: np.ndarray) -> np.ndarray:
        """
        Merge drawing canvas onto video frame.
        """
        if self.whiteboard_mode:
            # Dark digital whiteboard view
            base = np.full_like(frame, 20)  # Dark charcoal canvas
            # Add subtle grid
            grid_step = 40
            base[::grid_step, :] = np.clip(base[::grid_step, :] + 12, 0, 255)
            base[:, ::grid_step] = np.clip(base[:, ::grid_step] + 12, 0, 255)
        else:
            base = frame.copy()

        # Canvas mask where pixels are drawn (non-black)
        gray_canvas = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray_canvas, 10, 255, cv2.THRESH_BINARY)
        inv_mask = cv2.bitwise_not(mask)

        # Composite drawn strokes over base frame
        bg = cv2.bitwise_and(base, base, mask=inv_mask)
        fg = cv2.bitwise_and(self.canvas, self.canvas, mask=mask)
        composite = cv2.add(bg, fg)

        # Draw top palette
        composite = self.draw_palette_ui(composite)

        return composite

    def save_artwork(self) -> Path:
        """Save current canvas drawing as an image file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = SNAPSHOT_DIR / f"canvas_{timestamp}.png"
        cv2.imwrite(str(filename), self.canvas)
        return filename
