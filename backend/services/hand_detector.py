"""
High-Precision MediaPipe 3D Hand Landmark Detector with Temporal EMA Smoothing.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import time
import cv2
import numpy as np

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

try:
    from backend.config import detection_settings, colors
except ImportError:
    from config import detection_settings, colors


@dataclass
class HandLandmarksData:
    handedness: str  # "Left" or "Right"
    landmarks_pixel: np.ndarray  # (21, 2) pixel coords (x, y)
    landmarks_world: np.ndarray  # (21, 3) 3D spatial coords (x, y, z)
    raw_normalized: np.ndarray  # (21, 3) raw MediaPipe normalized coords (0..1)
    bbox: Tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    hand_scale: float  # Euclidean distance between Wrist (0) and Middle MCP (9)


HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
    (0, 17),                               # Palm Base
]


class HandDetector:
    def __init__(
        self,
        model_path: str = detection_settings.model_path,
        num_hands: int = detection_settings.num_hands,
        min_detection_confidence: float = detection_settings.min_hand_detection_confidence,
        min_tracking_confidence: float = detection_settings.min_tracking_confidence,
        smoothing_factor: float = 0.82,
        inference_size: Tuple[int, int] = (320, 240),
    ):
        self.smoothing_factor = smoothing_factor
        self.inference_size = inference_size
        self._prev_landmarks: Dict[str, np.ndarray] = {}
        self._last_ts = 0

        try:
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_hands=num_hands,
                min_hand_detection_confidence=min_detection_confidence,
                min_hand_presence_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
            self.landmarker = vision.HandLandmarker.create_from_options(options)
        except Exception as e:
            print(f"[HandDetector Warning] Could not load HandLandmarker ({model_path}): {e}")
            self.landmarker = None

    def process_frame(self, frame: np.ndarray) -> List[HandLandmarksData]:
        """Detect and extract hand landmarks with scale restoration and EMA smoothing."""
        if self.landmarker is None:
            return []
        h, w = frame.shape[:2]
        now_ms = int(time.perf_counter() * 1000)
        if now_ms <= self._last_ts:
            now_ms = self._last_ts + 1
        self._last_ts = now_ms
        timestamp_ms = now_ms

        # Downscale for ultra-fast MediaPipe inference (320x240 is 3x faster)
        inf_w, inf_h = self.inference_size
        small_frame = cv2.resize(frame, (inf_w, inf_h), interpolation=cv2.INTER_LINEAR)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        try:
            result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        except Exception as e:
            return []

        detected_hands: List[HandLandmarksData] = []
        if not result.hand_landmarks:
            self._prev_landmarks.clear()
            return detected_hands

        for idx, landmarks in enumerate(result.hand_landmarks):
            handedness = "Right"
            if result.handedness and idx < len(result.handedness):
                handedness = result.handedness[idx][0].category_name

            # Extract normalized coordinates (21, 3)
            raw_norm = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)

            # Map to camera resolution
            curr_pixels = np.zeros((21, 2), dtype=np.float32)
            curr_pixels[:, 0] = raw_norm[:, 0] * w
            curr_pixels[:, 1] = raw_norm[:, 1] * h

            # Exponential Moving Average (EMA) smoothing to eliminate micro-jitter
            if handedness in self._prev_landmarks:
                alpha = self.smoothing_factor
                smoothed_pixels = alpha * curr_pixels + (1.0 - alpha) * self._prev_landmarks[handedness]
            else:
                smoothed_pixels = curr_pixels
            self._prev_landmarks[handedness] = smoothed_pixels

            # 3D spatial world landmarks
            if result.hand_world_landmarks and idx < len(result.hand_world_landmarks):
                world_lm = np.array([[lm.x, lm.y, lm.z] for lm in result.hand_world_landmarks[idx]], dtype=np.float32)
            else:
                world_lm = raw_norm.copy()

            # Bounding Box
            x_min = int(np.clip(np.min(smoothed_pixels[:, 0]) - 20, 0, w))
            y_min = int(np.clip(np.min(smoothed_pixels[:, 1]) - 20, 0, h))
            x_max = int(np.clip(np.max(smoothed_pixels[:, 0]) + 20, 0, w))
            y_max = int(np.clip(np.max(smoothed_pixels[:, 1]) + 20, 0, h))

            # Scale metric: Wrist (0) to Middle MCP (9)
            wrist = smoothed_pixels[0]
            middle_mcp = smoothed_pixels[9]
            hand_scale = float(np.linalg.norm(middle_mcp - wrist))
            if hand_scale < 1.0:
                hand_scale = 1.0

            detected_hands.append(
                HandLandmarksData(
                    handedness=handedness,
                    landmarks_pixel=smoothed_pixels,
                    landmarks_world=world_lm,
                    raw_normalized=raw_norm,
                    bbox=(x_min, y_min, x_max, y_max),
                    hand_scale=hand_scale,
                )
            )

        return detected_hands

    def draw_landmarks(self, frame: np.ndarray, hands: List[HandLandmarksData]) -> np.ndarray:
        """Render modern, glowing hand skeleton and landmarks onto frame."""
        output = frame.copy()

        for hand in hands:
            pts = hand.landmarks_pixel.astype(int)
            accent = colors.PRIMARY if hand.handedness == "Right" else colors.SECONDARY

            # Draw bones
            for p1, p2 in HAND_CONNECTIONS:
                pt1 = tuple(pts[p1])
                pt2 = tuple(pts[p2])
                # Base bone line
                cv2.line(output, pt1, pt2, accent, 2, cv2.LINE_AA)

            # Draw landmark nodes with joint-specific styling
            for i, (x, y) in enumerate(pts):
                # Fingertips
                if i in [4, 8, 12, 16, 20]:
                    cv2.circle(output, (x, y), 6, colors.CYAN, -1, cv2.LINE_AA)
                    cv2.circle(output, (x, y), 8, (255, 255, 255), 1, cv2.LINE_AA)
                # Wrist
                elif i == 0:
                    cv2.circle(output, (x, y), 7, colors.GOLD, -1, cv2.LINE_AA)
                # Intermediate joints
                else:
                    cv2.circle(output, (x, y), 4, (240, 240, 240), -1, cv2.LINE_AA)

            # Draw sleek bounding box & Handedness tag
            x1, y1, x2, y2 = hand.bbox
            cv2.rectangle(output, (x1, y1), (x2, y2), accent, 1, cv2.LINE_AA)

            # Corner accents
            line_len = 16
            cv2.line(output, (x1, y1), (x1 + line_len, y1), accent, 2)
            cv2.line(output, (x1, y1), (x1, y1 + line_len), accent, 2)
            cv2.line(output, (x2, y1), (x2 - line_len, y1), accent, 2)
            cv2.line(output, (x2, y1), (x2, y1 + line_len), accent, 2)
            cv2.line(output, (x1, y2), (x1 + line_len, y2), accent, 2)
            cv2.line(output, (x1, y2), (x1, y2 - line_len), accent, 2)
            cv2.line(output, (x2, y2), (x2 - line_len, y2), accent, 2)
            cv2.line(output, (x2, y2), (x2, y2 - line_len), accent, 2)

            tag = f"{hand.handedness} Hand"
            cv2.putText(
                output,
                tag,
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                accent,
                1,
                cv2.LINE_AA,
            )

        return output

    def close(self):
        """Release MediaPipe resources."""
        if hasattr(self, "landmarker") and self.landmarker:
            self.landmarker.close()
