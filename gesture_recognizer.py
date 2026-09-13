"""
Gesture Recognition Engine for OmniGesture AI Studio.
Optimized for rapid gesture triggering, scale invariance, and low latency.
"""
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple
import math
import time
import numpy as np

from hand_tracker import (
    HandData,
    WRIST,
    THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP,
    INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP,
    MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP,
    RING_MCP, RING_PIP, RING_DIP, RING_TIP,
    PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP,
)


@dataclass
class FingerStates:
    thumb: bool
    index: bool
    middle: bool
    ring: bool
    pinky: bool

    @property
    def count_extended(self) -> int:
        return sum([self.thumb, self.index, self.middle, self.ring, self.pinky])

    @property
    def vector(self) -> List[int]:
        return [int(self.thumb), int(self.index), int(self.middle), int(self.ring), int(self.pinky)]


@dataclass
class GestureResult:
    name: str
    confidence: float
    finger_states: FingerStates
    is_pinch: bool
    pinch_distance_ratio: float
    dynamic_gesture: Optional[str] = None
    finger_angles: Dict[str, float] = field(default_factory=dict)


def compute_angle_3points(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """Compute the angle at vertex p2 formed by (p1, p2, p3) in degrees."""
    v1 = p1 - p2
    v2 = p3 - p2
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 < 1e-6 or norm2 < 1e-6:
        return 0.0
    cosine = np.dot(v1, v2) / (norm1 * norm2)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


class DynamicMotionTracker:
    """Tracks trajectory history to detect dynamic gestures like swipes and waves."""

    def __init__(self, history_len: int = 8, cooldown_sec: float = 0.4):
        self.history_len = history_len
        self.cooldown_sec = cooldown_sec
        self.history: Deque[Tuple[float, float, float]] = deque(maxlen=history_len)
        self.last_trigger_time = 0.0
        self.last_gesture: Optional[str] = None

    def update(self, center_norm: Tuple[float, float], hand_size: float) -> Optional[str]:
        now = time.time()
        self.history.append((now, center_norm[0], center_norm[1]))

        if (now - self.last_trigger_time) < self.cooldown_sec:
            return None

        if len(self.history) < self.history_len:
            return None

        t_old, x_old, y_old = self.history[0]
        t_cur, x_cur, y_cur = self.history[-1]
        dt = t_cur - t_old
        if dt < 0.05 or dt > 0.6:
            return None

        dx = (x_cur - x_old) / max(hand_size, 0.05)
        dy = (y_cur - y_old) / max(hand_size, 0.05)
        speed = math.hypot(dx, dy) / dt

        if speed > 1.8:
            if abs(dx) > abs(dy) * 1.3 and abs(dx) > 0.35:
                gesture = "SWIPE_RIGHT" if dx > 0 else "SWIPE_LEFT"
                self.last_trigger_time = now
                self.last_gesture = gesture
                self.history.clear()
                return gesture
            elif abs(dy) > abs(dx) * 1.3 and abs(dy) > 0.35:
                gesture = "SWIPE_DOWN" if dy > 0 else "SWIPE_UP"
                self.last_trigger_time = now
                self.last_gesture = gesture
                self.history.clear()
                return gesture

        return None

    def reset(self):
        self.history.clear()


class GestureRecognizer:
    """Fast, scale-invariant gesture classifier."""

    def __init__(self):
        self.motion_trackers: Dict[str, DynamicMotionTracker] = {}

    def _determine_finger_states(self, lm: np.ndarray, hand_size: float, handedness: str) -> FingerStates:
        wrist = lm[WRIST, :2]

        def is_finger_extended(tip_idx: int, pip_idx: int, mcp_idx: int) -> bool:
            dist_tip = np.linalg.norm(lm[tip_idx, :2] - wrist)
            dist_pip = np.linalg.norm(lm[pip_idx, :2] - wrist)
            dist_mcp = np.linalg.norm(lm[mcp_idx, :2] - wrist)
            return (dist_tip > dist_pip * 1.08) and (dist_tip > dist_mcp * 1.20)

        index_ext = is_finger_extended(INDEX_TIP, INDEX_PIP, INDEX_MCP)
        middle_ext = is_finger_extended(MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP)
        ring_ext = is_finger_extended(RING_TIP, RING_PIP, RING_MCP)
        pinky_ext = is_finger_extended(PINKY_TIP, PINKY_PIP, PINKY_MCP)

        # Thumb detection
        thumb_tip = lm[THUMB_TIP, :2]
        thumb_ip = lm[THUMB_IP, :2]
        pinky_mcp = lm[PINKY_MCP, :2]
        dist_thumb_pinky = np.linalg.norm(thumb_tip - pinky_mcp)
        dist_thumb_ip_pinky = np.linalg.norm(thumb_ip - pinky_mcp)
        thumb_angle = compute_angle_3points(lm[THUMB_MCP, :2], lm[THUMB_IP, :2], thumb_tip)
        thumb_ext = (dist_thumb_pinky > dist_thumb_ip_pinky * 1.05) and (thumb_angle > 135)

        return FingerStates(
            thumb=bool(thumb_ext),
            index=bool(index_ext),
            middle=bool(middle_ext),
            ring=bool(ring_ext),
            pinky=bool(pinky_ext),
        )

    def recognize(self, hand: HandData) -> GestureResult:
        lm = hand.landmarks_norm
        hand_size = hand.hand_size
        handedness = hand.handedness

        if handedness not in self.motion_trackers:
            self.motion_trackers[handedness] = DynamicMotionTracker()
        norm_center = (float(lm[WRIST, 0] + lm[MIDDLE_MCP, 0]) / 2.0,
                       float(lm[WRIST, 1] + lm[MIDDLE_MCP, 1]) / 2.0)
        dynamic_gesture = self.motion_trackers[handedness].update(norm_center, hand_size)

        finger_states = self._determine_finger_states(lm, hand_size, handedness)
        v = finger_states.vector

        pinch_dist = float(np.linalg.norm(lm[THUMB_TIP, :2] - lm[INDEX_TIP, :2]))
        pinch_ratio = pinch_dist / max(hand_size, 1e-4)
        is_pinch = pinch_ratio < 0.28

        angles = {
            "index": compute_angle_3points(lm[INDEX_MCP, :2], lm[INDEX_PIP, :2], lm[INDEX_TIP, :2]),
            "middle": compute_angle_3points(lm[MIDDLE_MCP, :2], lm[MIDDLE_PIP, :2], lm[MIDDLE_TIP, :2]),
            "ring": compute_angle_3points(lm[RING_MCP, :2], lm[RING_PIP, :2], lm[RING_TIP, :2]),
            "pinky": compute_angle_3points(lm[PINKY_MCP, :2], lm[PINKY_PIP, :2], lm[PINKY_TIP, :2]),
        }

        thumb_vec = lm[THUMB_TIP, :2] - lm[THUMB_MCP, :2]
        gesture_name = "UNKNOWN"
        confidence = 0.70

        if v == [0, 0, 0, 0, 0]:
            gesture_name = "FIST"
            confidence = 0.95
        elif is_pinch and (finger_states.middle or finger_states.ring or finger_states.pinky):
            gesture_name = "OK_SIGN"
            confidence = 0.94
        elif is_pinch and (finger_states.index or finger_states.thumb):
            gesture_name = "PINCH"
            confidence = 0.92
        elif v == [1, 1, 1, 1, 1] or v == [0, 1, 1, 1, 1]:
            gesture_name = "OPEN_PALM"
            confidence = 0.96
        elif (v == [0, 1, 1, 0, 0] or v == [1, 1, 1, 0, 0]) and not is_pinch:
            separation = np.linalg.norm(lm[INDEX_TIP, :2] - lm[MIDDLE_TIP, :2]) / hand_size
            if separation > 0.16:
                gesture_name = "VICTORY"
                confidence = 0.95
            else:
                gesture_name = "PEACE"
                confidence = 0.92
        elif v == [1, 0, 0, 0, 0]:
            if thumb_vec[1] < -0.04:
                gesture_name = "THUMBS_UP"
                confidence = 0.94
            elif thumb_vec[1] > 0.04:
                gesture_name = "THUMBS_DOWN"
                confidence = 0.94
            else:
                gesture_name = "THUMB"
                confidence = 0.85
        elif (v == [0, 1, 0, 0, 0] or v == [1, 1, 0, 0, 0]) and not is_pinch:
            index_dir = lm[INDEX_TIP, :2] - lm[INDEX_MCP, :2]
            if abs(index_dir[1]) > abs(index_dir[0]):
                gesture_name = "POINTING_UP" if index_dir[1] < 0 else "POINTING_DOWN"
            else:
                gesture_name = "POINTING_RIGHT" if index_dir[0] > 0 else "POINTING_LEFT"
            confidence = 0.93
        elif v == [0, 1, 0, 0, 1] or v == [1, 1, 0, 0, 1]:
            gesture_name = "ROCK_ON"
            confidence = 0.92
        elif v == [1, 0, 0, 0, 1]:
            gesture_name = "CALL_ME"
            confidence = 0.90
        elif v == [1, 1, 0, 0, 0] and not is_pinch:
            gesture_name = "GUN"
            confidence = 0.88
        elif finger_states.count_extended > 0:
            gesture_name = f"{finger_states.count_extended}_FINGERS"
            confidence = 0.82

        return GestureResult(
            name=gesture_name,
            confidence=confidence,
            finger_states=finger_states,
            is_pinch=is_pinch,
            pinch_distance_ratio=pinch_ratio,
            dynamic_gesture=dynamic_gesture,
            finger_angles=angles,
        )

    def reset(self):
        for tracker in self.motion_trackers.values():
            tracker.reset()
        self.motion_trackers.clear()
