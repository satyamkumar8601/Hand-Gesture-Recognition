"""
Visual HUD (Heads-Up Display) and Futuristic Overlay Renderer.
Renders glowing hand skeletons, cyberpunk data cards, gesture badges, and telemetry.
"""
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from config import AppConfig
from hand_tracker import (
    HandData,
    HAND_CONNECTIONS,
    WRIST,
    INDEX_TIP,
    THUMB_TIP,
    MIDDLE_TIP,
    RING_TIP,
    PINKY_TIP,
)
from gesture_recognizer import GestureResult


class HUDRenderer:
    """Renders high-tech HUD cards, skeletons, and telemetry overlays."""

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.fps_history: List[float] = []
        self.notification_text: Optional[str] = None
        self.notification_expiry: float = 0.0
        self.show_help = False

    def notify(self, message: str, duration: float = 2.0):
        import time
        self.notification_text = message
        self.notification_expiry = time.time() + duration

    def draw_skeleton(self, frame: np.ndarray, hand: HandData, color_accent: Tuple[int, int, int]) -> np.ndarray:
        """Draw glowing cyberpunk hand skeleton and joint nodes."""
        lm = hand.landmarks_pixel

        # Draw bones (connections) with double pass for neon glow effect
        for p1_idx, p2_idx in HAND_CONNECTIONS:
            pt1 = (int(lm[p1_idx][0]), int(lm[p1_idx][1]))
            pt2 = (int(lm[p2_idx][0]), int(lm[p2_idx][1]))

            # Subtle glow line
            cv2.line(frame, pt1, pt2, (20, 20, 20), 4, cv2.LINE_AA)
            cv2.line(frame, pt1, pt2, color_accent, 2, cv2.LINE_AA)

        # Draw landmark nodes
        for idx, (x, y) in enumerate(lm):
            pt = (int(x), int(y))
            # Highlight fingertips with distinct glow
            if idx in [THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]:
                cv2.circle(frame, pt, 8, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, pt, 11, color_accent, 2, cv2.LINE_AA)
            else:
                cv2.circle(frame, pt, 4, color_accent, -1, cv2.LINE_AA)
                cv2.circle(frame, pt, 5, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    def draw_bounding_box(self, frame: np.ndarray, hand: HandData, label: str) -> np.ndarray:
        """Draw high-tech bracketed corner bounding box."""
        x1, y1, x2, y2 = hand.bbox
        corner_len = min(25, (x2 - x1) // 4, (y2 - y1) // 4)
        color = AppConfig.colors.CYAN if hand.handedness == "Right" else AppConfig.colors.NEON_PINK

        # Draw 4 stylish bracket corners
        # Top-Left
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, 2, cv2.LINE_AA)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, 2, cv2.LINE_AA)
        # Top-Right
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, 2, cv2.LINE_AA)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, 2, cv2.LINE_AA)
        # Bottom-Left
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, 2, cv2.LINE_AA)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, 2, cv2.LINE_AA)
        # Bottom-Right
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, 2, cv2.LINE_AA)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, 2, cv2.LINE_AA)

        # Handedness badge above box
        badge_text = f"{hand.handedness} ({int(hand.handedness_score * 100)}%)"
        cv2.putText(
            frame,
            badge_text,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )
        return frame

    def draw_gesture_card(
        self,
        frame: np.ndarray,
        hand: HandData,
        gesture: GestureResult,
        slot_idx: int = 0
    ) -> np.ndarray:
        """Draw floating glassmorphism card for recognized gesture and metrics."""
        card_w, card_h = 280, 130
        margin = 15
        x = self.width - card_w - margin
        y = margin + slot_idx * (card_h + 10)

        # Glass background (ROI slice optimization avoids full frame memory copy)
        h_f, w_f = frame.shape[:2]
        if y + card_h <= h_f and x + card_w <= w_f and x >= 0 and y >= 0:
            sub = frame[y : y + card_h, x : x + card_w]
            overlay = sub.copy()
            cv2.rectangle(overlay, (0, 0), (card_w, card_h), (20, 18, 22), -1)
            cv2.addWeighted(overlay, 0.75, sub, 0.25, 0, dst=sub)
            cv2.rectangle(frame, (x, y), (x + card_w, y + card_h), (60, 60, 80), 1)

        # Header: Hand identity
        accent = AppConfig.colors.CYAN if hand.handedness == "Right" else AppConfig.colors.NEON_PINK
        cv2.putText(frame, f"// {hand.handedness.upper()} HAND", (x + 12, y + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, accent, 1, cv2.LINE_AA)

        # Gesture Name
        clean_name = gesture.name.replace("_", " ")
        cv2.putText(frame, clean_name, (x + 12, y + 54),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)

        # Confidence Bar
        bar_x = x + 12
        bar_y = y + 68
        bar_w = card_w - 24
        bar_h = 6
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
        fill_w = int(bar_w * gesture.confidence)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), AppConfig.colors.EMERALD_GREEN, -1)

        # Finger Extension Indicators: [T, I, M, R, P]
        f_states = gesture.finger_states
        labels = [("T", f_states.thumb), ("I", f_states.index),
                  ("M", f_states.middle), ("R", f_states.ring), ("P", f_states.pinky)]

        fx = x + 14
        fy = y + 102
        cv2.putText(frame, "FINGERS:", (fx, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1, cv2.LINE_AA)
        fx += 65
        for tag, state in labels:
            col = AppConfig.colors.EMERALD_GREEN if state else (70, 70, 70)
            cv2.circle(frame, (fx, fy - 4), 6, col, -1, cv2.LINE_AA)
            cv2.putText(frame, tag, (fx - 4, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
            fx += 22

        # Pinch ratio readout
        pinch_str = f"Pinch: {gesture.pinch_distance_ratio:.2f}"
        cv2.putText(frame, pinch_str, (x + card_w - 90, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    AppConfig.colors.GOLD_YELLOW if gesture.is_pinch else (150, 150, 150), 1, cv2.LINE_AA)

        return frame

    def draw_top_telemetry(self, frame: np.ndarray, fps: float, active_mode_name: str) -> np.ndarray:
        """Render top left status banner (FPS, Mode, Status)."""
        card_w, card_h = 320, 64
        x, y = 15, 15

        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + card_w, y + card_h), (20, 18, 22), -1)
        frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)
        cv2.rectangle(frame, (x, y), (x + card_w, y + card_h), (60, 60, 80), 1)

        # Title / Project badge
        cv2.putText(frame, "OMNIGESTURE AI", (x + 12, y + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, AppConfig.colors.CYAN, 2, cv2.LINE_AA)

        # Active Mode pill
        cv2.putText(frame, f"MODE: {active_mode_name}", (x + 12, y + 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, AppConfig.colors.GOLD_YELLOW, 1, cv2.LINE_AA)

        # FPS counter
        fps_text = f"FPS: {int(fps)}"
        cv2.putText(frame, fps_text, (x + card_w - 85, y + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, AppConfig.colors.EMERALD_GREEN, 2, cv2.LINE_AA)

        # Key help prompt
        cv2.putText(frame, "Press 'h' for Help", (x + card_w - 115, y + 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 160, 160), 1, cv2.LINE_AA)

        # Draw toast notification if active
        import time
        if self.notification_text and time.time() < self.notification_expiry:
            toast_w = 400
            toast_h = 42
            tx = (self.width - toast_w) // 2
            ty = self.height - 70
            cv2.rectangle(frame, (tx, ty), (tx + toast_w, ty + toast_h), (30, 30, 40), -1)
            cv2.rectangle(frame, (tx, ty), (tx + toast_w, ty + toast_h), AppConfig.colors.CYAN, 1)
            cv2.putText(frame, self.notification_text, (tx + 18, ty + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    def draw_help_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Render modal overlay listing keyboard shortcuts and gesture mappings."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (10, 10, 15), -1)
        frame = cv2.addWeighted(overlay, 0.88, frame, 0.12, 0)

        box_w, box_h = 760, 480
        bx = (self.width - box_w) // 2
        by = (self.height - box_h) // 2

        cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), (30, 32, 40), -1)
        cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), AppConfig.colors.CYAN, 2)

        cv2.putText(frame, "OMNIGESTURE AI // COMMAND & GESTURE GUIDE", (bx + 25, by + 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.line(frame, (bx + 25, by + 60), (bx + box_w - 25, by + 60), (70, 70, 90), 1)

        help_sections = [
            ("KEYBOARD SHORTCUTS", [
                ("1", "HUD / Analytics Mode"),
                ("2", "Air Canvas Mode (Virtual Whiteboard)"),
                ("3", "Virtual Mouse Mode"),
                ("4", "Finger Counter & Rehab Mode"),
                ("c", "Clear Canvas (in Air Canvas mode)"),
                ("u", "Undo last stroke"),
                ("b", "Toggle Dark Whiteboard / Camera background"),
                ("s", "Save high-res Snapshot to disk"),
                ("m", "Toggle Mouse Control on/off"),
                ("p / Space", "Pause & Turn OFF Camera (Standby)"),
                ("h", "Toggle this Help Drawer"),
                ("q / ESC", "Exit Application"),
            ]),
            ("GESTURE CONTROLS", [
                ("Index Pointing", "Draw on canvas / Move cursor"),
                ("Index + Middle (Peace)", "Selection / Hover / Mouse Scroll"),
                ("Thumb + Index Pinch", "Adjust brush size / Mouse Left Click & Drag"),
                ("OK Sign", "Mouse Right Click"),
                ("Fist", "Pause drawing / Hold for Undo"),
                ("Swipe Left / Right", "Next / Previous Presentation Slide"),
            ]),
        ]

        col1_x = bx + 30
        col2_x = bx + box_w // 2 + 10
        cur_y = by + 90

        for col_idx, (title, items) in enumerate(help_sections):
            cx = col1_x if col_idx == 0 else col2_x
            y = cur_y
            cv2.putText(frame, title, (cx, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, AppConfig.colors.GOLD_YELLOW, 2, cv2.LINE_AA)
            y += 25
            for key, desc in items:
                cv2.putText(frame, f"{key}:", (cx, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, AppConfig.colors.CYAN, 1, cv2.LINE_AA)
                cv2.putText(frame, desc, (cx + 90, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA)
                y += 24

        cv2.putText(frame, "[Press 'h' or 'ESC' to close this guide]", (bx + box_w // 2 - 140, by + box_h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1, cv2.LINE_AA)

        return frame
