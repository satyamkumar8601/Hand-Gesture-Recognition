"""
Rehabilitation & Hand Biometrics Tracker.
Calculates finger extension counts, grip closure percentage, range-of-motion (ROM)
angles, and provides real-time biomechanical feedback.
"""
from typing import Dict, List, Tuple
import cv2
import numpy as np

from config import AppConfig
from hand_tracker import HandData, WRIST, MIDDLE_MCP, INDEX_TIP, THUMB_TIP
from gesture_recognizer import GestureResult


class RehabTracker:
    """Computes biomechanical and therapeutic metrics from hand landmarks."""

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height

    def compute_grip_closure(self, hand: HandData) -> float:
        """
        Calculates hand grip closure percentage (0% = fully open hand, 100% = tight fist).
        """
        lm = hand.landmarks_norm
        wrist = lm[WRIST, :2]
        hand_size = max(hand.hand_size, 1e-4)

        # Average distance from wrist to all 5 fingertips
        tip_indices = [4, 8, 12, 16, 20]
        distances = [np.linalg.norm(lm[i, :2] - wrist) for i in tip_indices]
        avg_dist = float(np.mean(distances)) / hand_size

        # In open palm, avg_dist is approx 1.6 - 1.9
        # In tight fist, avg_dist is approx 0.5 - 0.7
        norm_grip = 1.0 - np.clip((avg_dist - 0.6) / (1.7 - 0.6), 0.0, 1.0)
        return float(norm_grip * 100.0)

    def draw_rehab_dashboard(
        self,
        frame: np.ndarray,
        hands: List[HandData],
        gestures: List[GestureResult],
    ) -> np.ndarray:
        """Render rehabilitation & biometric inspection panel."""
        panel_w, panel_h = 360, 240
        x = 20
        y = self.height - panel_h - 20

        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + panel_w, y + panel_h), (20, 22, 28), -1)
        frame = cv2.addWeighted(overlay, 0.82, frame, 0.18, 0)
        cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), AppConfig.colors.CYAN, 1)

        # Title
        cv2.putText(frame, "// BIOMETRIC & REHAB ANALYTICS", (x + 14, y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, AppConfig.colors.CYAN, 2, cv2.LINE_AA)

        if not hands:
            cv2.putText(frame, "Waiting for hand detection...", (x + 14, y + 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA)
            return frame

        # Calculate total extended fingers across all detected hands
        total_fingers = sum(g.finger_states.count_extended for g in gestures)
        cv2.putText(frame, f"EXTENDED FINGERS: {total_fingers} / 10", (x + 14, y + 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        cur_y = y + 95
        for idx, (hand, gesture) in enumerate(zip(hands, gestures)):
            if idx >= 2:
                break
            grip_pct = self.compute_grip_closure(hand)
            accent = AppConfig.colors.CYAN if hand.handedness == "Right" else AppConfig.colors.NEON_PINK

            # Hand label
            cv2.putText(frame, f"{hand.handedness.upper()} HAND - Grip Closure: {int(grip_pct)}%",
                        (x + 14, cur_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, accent, 1, cv2.LINE_AA)

            # Grip closure progress bar
            bar_x = x + 14
            bar_y = cur_y + 8
            bar_w = panel_w - 28
            bar_h = 8
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 60), -1)
            fill_w = int(bar_w * (grip_pct / 100.0))
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h),
                          AppConfig.colors.EMERALD_GREEN if grip_pct < 80 else AppConfig.colors.GOLD_YELLOW, -1)

            # Joint ROM (Range of motion) angles
            angles = gesture.finger_angles
            angle_str = f"Index: {int(angles.get('index', 0))}° | Mid: {int(angles.get('middle', 0))}° | Ring: {int(angles.get('ring', 0))}°"
            cv2.putText(frame, angle_str, (x + 14, cur_y + 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)

            cur_y += 65

        return frame
