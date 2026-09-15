"""
Hand tracking module leveraging Google MediaPipe Tasks HandLandmarker.
Optimized for ultra-low latency, adaptive jitter smoothing, and high responsiveness.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os
os.environ["GLOG_minloglevel"] = "3"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"

import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

# Landmark index constants
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

# Canonical hand skeleton connection pairs
HAND_CONNECTIONS = [
    (WRIST, THUMB_CMC),
    (WRIST, INDEX_MCP),
    (INDEX_MCP, MIDDLE_MCP),
    (MIDDLE_MCP, RING_MCP),
    (RING_MCP, PINKY_MCP),
    (WRIST, PINKY_MCP),
    (THUMB_CMC, THUMB_MCP),
    (THUMB_MCP, THUMB_IP),
    (THUMB_IP, THUMB_TIP),
    (INDEX_MCP, INDEX_PIP),
    (INDEX_PIP, INDEX_DIP),
    (INDEX_DIP, INDEX_TIP),
    (MIDDLE_MCP, MIDDLE_PIP),
    (MIDDLE_PIP, MIDDLE_DIP),
    (MIDDLE_DIP, MIDDLE_TIP),
    (RING_MCP, RING_PIP),
    (RING_PIP, RING_DIP),
    (RING_DIP, RING_TIP),
    (PINKY_MCP, PINKY_PIP),
    (PINKY_PIP, PINKY_DIP),
    (PINKY_DIP, PINKY_TIP),
]

FINGER_TIPS = [THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_PIPS = [THUMB_IP, INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]
FINGER_MCPS = [THUMB_MCP, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]


@dataclass
class HandData:
    """Encapsulates processed information for a detected hand."""
    handedness: str
    handedness_score: float
    landmarks_norm: np.ndarray  # (21, 3) normalized [0, 1] (x, y, z)
    landmarks_pixel: np.ndarray  # (21, 2) pixel coordinates (x, y)
    bbox: Tuple[int, int, int, int]
    hand_size: float
    palm_center: Tuple[int, int]


class AdaptiveLandmarkSmoother:
    """
    Adaptive Exponential Moving Average filter.
    Increases responsiveness during fast movement and suppresses jitter when still.
    """

    def __init__(self, base_alpha: float = 0.75):
        self.base_alpha = base_alpha
        self.prev_landmarks: Dict[str, np.ndarray] = {}

    def smooth(self, hand_id: str, current_landmarks: np.ndarray) -> np.ndarray:
        if hand_id not in self.prev_landmarks:
            self.prev_landmarks[hand_id] = current_landmarks.copy()
            return current_landmarks

        # Calculate movement magnitude at wrist and index tip
        prev = self.prev_landmarks[hand_id]
        movement = np.linalg.norm(current_landmarks[INDEX_TIP, :2] - prev[INDEX_TIP, :2])

        # If moving quickly, boost alpha to 0.92 for zero-lag tracking; if still, drop to 0.6 for stability
        dynamic_alpha = np.clip(self.base_alpha + movement * 4.0, 0.60, 0.95)

        smoothed = dynamic_alpha * current_landmarks + (1.0 - dynamic_alpha) * prev
        self.prev_landmarks[hand_id] = smoothed
        return smoothed

    def reset(self, active_hand_ids: Optional[List[str]] = None):
        if active_hand_ids is None:
            self.prev_landmarks.clear()
        else:
            to_remove = [k for k in self.prev_landmarks if k not in active_hand_ids]
            for k in to_remove:
                del self.prev_landmarks[k]


class HandTracker:
    """High-performance wrapper around MediaPipe Vision HandLandmarker task."""

    def __init__(
        self,
        model_path: str = "hand_landmarker.task",
        num_hands: int = 2,
        min_detection_confidence: float = 0.50,
        min_tracking_confidence: float = 0.50,
        smoothing_factor: float = 0.75,
        inference_size: Tuple[int, int] = (480, 360),
    ):
        model_file = Path(model_path).resolve()
        if not model_file.exists():
            # Check backend directory if relative path didn't resolve
            backend_model = Path(__file__).resolve().parent / "hand_landmarker.task"
            if backend_model.exists():
                model_file = backend_model
            else:
                raise FileNotFoundError(f"MediaPipe model asset not found at {model_file}")

        self.model_path = str(model_file)
        self.num_hands = num_hands
        self.inference_size = inference_size
        self.smoother = AdaptiveLandmarkSmoother(base_alpha=smoothing_factor)

        base_options = BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        self.detector = vision.HandLandmarker.create_from_options(options)
        self.start_time = time.time()
        self.last_timestamp_ms = -1

    def process_frame(self, frame_bgr: np.ndarray) -> List[HandData]:
        """
        Process a BGR video frame and return structured hand tracking data with zero latency.
        """
        h, w, _ = frame_bgr.shape

        # Downscale for inference to accelerate MediaPipe processing
        infer_w, infer_h = self.inference_size
        if (w, h) != (infer_w, infer_h):
            infer_bgr = cv2.resize(frame_bgr, (infer_w, infer_h), interpolation=cv2.INTER_LINEAR)
        else:
            infer_bgr = frame_bgr

        frame_rgb = cv2.cvtColor(infer_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # Strictly ensure monotonically increasing timestamps for MediaPipe
        now_ms = int((time.time() - self.start_time) * 1000)
        if now_ms <= self.last_timestamp_ms:
            now_ms = self.last_timestamp_ms + 1
        self.last_timestamp_ms = now_ms

        # Detect landmarks
        result = self.detector.detect_for_video(mp_image, now_ms)

        hands_data: List[HandData] = []
        if not result.hand_landmarks:
            self.smoother.reset([])
            return hands_data

        active_labels: List[str] = []

        for idx, landmarks in enumerate(result.hand_landmarks):
            # Extract handedness
            if result.handedness and idx < len(result.handedness) and result.handedness[idx]:
                category = result.handedness[idx][0]
                handedness = category.category_name
                handedness_score = category.score
            else:
                handedness = f"Hand_{idx}"
                handedness_score = 0.9

            active_labels.append(handedness)

            # Raw normalized coordinates array (21, 3)
            raw_norm = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)

            # Adaptive temporal smoothing
            smoothed_norm = self.smoother.smooth(handedness, raw_norm)

            # Map normalized coordinates back to display frame resolution (w, h)
            pixel_x = np.clip(smoothed_norm[:, 0] * w, 0, w - 1).astype(np.int32)
            pixel_y = np.clip(smoothed_norm[:, 1] * h, 0, h - 1).astype(np.int32)
            pixel_coords = np.column_stack((pixel_x, pixel_y))

            # Compute bounding box
            xmin, xmax = int(pixel_x.min()), int(pixel_x.max())
            ymin, ymax = int(pixel_y.min()), int(pixel_y.max())
            padding_x = int((xmax - xmin) * 0.12)
            padding_y = int((ymax - ymin) * 0.12)
            bbox = (
                max(0, xmin - padding_x),
                max(0, ymin - padding_y),
                min(w - 1, xmax + padding_x),
                min(h - 1, ymax + padding_y),
            )

            # Scale reference
            hand_size = float(np.linalg.norm(smoothed_norm[MIDDLE_MCP, :2] - smoothed_norm[WRIST, :2]))
            if hand_size < 1e-4:
                hand_size = 0.1

            # Palm center
            palm_px = int(np.mean(pixel_coords[[WRIST, INDEX_MCP, PINKY_MCP], 0]))
            palm_py = int(np.mean(pixel_coords[[WRIST, INDEX_MCP, PINKY_MCP], 1]))

            hands_data.append(
                HandData(
                    handedness=handedness,
                    handedness_score=handedness_score,
                    landmarks_norm=smoothed_norm,
                    landmarks_pixel=pixel_coords,
                    bbox=bbox,
                    hand_size=hand_size,
                    palm_center=(palm_px, palm_py),
                )
            )

        self.smoother.reset(active_labels)
        return hands_data

    def close(self):
        if hasattr(self, "detector") and self.detector:
            self.detector.close()
