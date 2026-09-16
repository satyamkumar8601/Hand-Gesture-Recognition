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
        model_path: Optional[str] = None,
        num_hands: int = detection_settings.num_hands,
        min_detection_confidence: float = 0.30,
        min_tracking_confidence: float = 0.30,
        smoothing_factor: float = 0.82,
        inference_size: Tuple[int, int] = (640, 480),
    ):
        self.smoothing_factor = smoothing_factor
        self.inference_size = inference_size
        self._prev_landmarks: Dict[str, np.ndarray] = {}
        self._last_ts = 0
        self._last_error = None

        # Resolve model path reliably across environments
        target_path = None
        candidates = [
            Path(model_path) if model_path else None,
            Path(detection_settings.model_path) if hasattr(detection_settings, "model_path") else None,
            Path(__file__).resolve().parent.parent / "hand_landmarker.task",
            Path(__file__).resolve().parent.parent.parent / "hand_landmarker.task",
            Path.cwd() / "hand_landmarker.task",
            Path.cwd() / "backend" / "hand_landmarker.task",
        ]
        for c in candidates:
            if c and c.exists() and c.stat().st_size > 1000:
                target_path = c
                break

        # Auto-download fallback if missing
        if target_path is None:
            fallback = Path(__file__).resolve().parent.parent / "hand_landmarker.task"
            try:
                import urllib.request
                print(f"[HandDetector] Downloading official MediaPipe task model to {fallback}...")
                model_url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
                urllib.request.urlretrieve(model_url, str(fallback))
                target_path = fallback
            except Exception as e:
                self._last_error = f"Model download failed: {e}"
                print(f"[HandDetector Error] Could not download task model: {e}")

        self.model_path = str(target_path) if target_path else ""
        self.landmarker = None
        self.image_landmarker = None

        # On Linux (Render cloud container), ensure libGLESv2.so.2 is globally preloaded
        import sys
        if sys.platform.startswith("linux"):
            libs_dir = Path(__file__).resolve().parent.parent / "libs"
            if libs_dir.exists():
                import ctypes
                for libname in ["libGLdispatch.so.0", "libGLESv2.so.2", "libEGL.so.1", "libGL.so.1"]:
                    lp = libs_dir / libname
                    if lp.exists():
                        try:
                            ctypes.CDLL(str(lp), mode=ctypes.RTLD_GLOBAL)
                        except Exception:
                            pass

        if target_path and target_path.exists():
            base_options = python.BaseOptions(model_asset_path=str(target_path))

            # 1. Image Mode Landmarker: Stateless, jitter-free, ideal for HTTP API / Base64 frames
            try:
                img_options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    num_hands=num_hands,
                    min_hand_detection_confidence=min_detection_confidence,
                    min_hand_presence_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence,
                )
                self.image_landmarker = vision.HandLandmarker.create_from_options(img_options)
            except Exception as e:
                self._last_error = f"Image landmarker init error: {e}"
                print(f"[HandDetector Warning] Could not load IMAGE HandLandmarker: {e}")

            # 2. Video Mode Landmarker: For local sequential OpenCV desktop feed
            try:
                video_options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.VIDEO,
                    num_hands=num_hands,
                    min_hand_detection_confidence=min_detection_confidence,
                    min_hand_presence_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence,
                )
                self.landmarker = vision.HandLandmarker.create_from_options(video_options)
            except Exception as e:
                print(f"[HandDetector Warning] Could not load VIDEO HandLandmarker: {e}")
        else:
            self._last_error = f"Task model file not found in candidates"
            print(f"[HandDetector Warning] Task model file not found: {self.model_path}")

    def process_image(self, frame: np.ndarray) -> List[HandLandmarksData]:
        """Stateless hand landmark detection for HTTP API frames."""
        if self.image_landmarker is None and self.landmarker is None:
            return []

        h, w = frame.shape[:2]
        inf_w, inf_h = self.inference_size
        if w > inf_w or h > inf_h:
            scale_f = min(inf_w / w, inf_h / h)
            nw = max(1, int(w * scale_f))
            nh = max(1, int(h * scale_f))
            small_frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        else:
            small_frame = frame

        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = None
        if self.image_landmarker is not None:
            try:
                result = self.image_landmarker.detect(mp_image)
            except Exception as e:
                self._last_error = f"image_landmarker error: {e}"
                result = None

        # Fallback to video landmarker if image landmarker unavailable
        if result is None and self.landmarker is not None:
            try:
                now_ms = int(time.perf_counter() * 1000)
                if now_ms <= self._last_ts:
                    now_ms = self._last_ts + 1
                self._last_ts = now_ms
                result = self.landmarker.detect_for_video(mp_image, now_ms)
            except Exception as e:
                self._last_error = f"fallback video error: {e}"
                return []

        if result is None or not result.hand_landmarks:
            return []

        detected_hands: List[HandLandmarksData] = []
        for idx, landmarks in enumerate(result.hand_landmarks):
            handedness = "Right"
            if result.handedness and idx < len(result.handedness):
                handedness = result.handedness[idx][0].category_name

            raw_norm = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)

            curr_pixels = np.zeros((21, 2), dtype=np.float32)
            curr_pixels[:, 0] = raw_norm[:, 0] * w
            curr_pixels[:, 1] = raw_norm[:, 1] * h

            if result.hand_world_landmarks and idx < len(result.hand_world_landmarks):
                world_lm = np.array([[lm.x, lm.y, lm.z] for lm in result.hand_world_landmarks[idx]], dtype=np.float32)
            else:
                world_lm = raw_norm.copy()

            x_min = int(np.clip(np.min(curr_pixels[:, 0]) - 20, 0, w))
            y_min = int(np.clip(np.min(curr_pixels[:, 1]) - 20, 0, h))
            x_max = int(np.clip(np.max(curr_pixels[:, 0]) + 20, 0, w))
            y_max = int(np.clip(np.max(curr_pixels[:, 1]) + 20, 0, h))

            wrist = curr_pixels[0]
            middle_mcp = curr_pixels[9]
            hand_scale = float(np.linalg.norm(middle_mcp - wrist))
            if hand_scale < 1.0:
                hand_scale = 1.0

            detected_hands.append(
                HandLandmarksData(
                    handedness=handedness,
                    landmarks_pixel=curr_pixels,
                    landmarks_world=world_lm,
                    raw_normalized=raw_norm,
                    bbox=(x_min, y_min, x_max, y_max),
                    hand_scale=hand_scale,
                )
            )

        # Sort so the foreground active hand is primary index 0
        detected_hands.sort(key=lambda h: h.hand_scale, reverse=True)
        return detected_hands

    def process_frame(self, frame: np.ndarray) -> List[HandLandmarksData]:
        """Detect and extract hand landmarks with scale restoration and EMA smoothing."""
        if self.landmarker is None:
            # Graceful fallback to stateless image landmarker
            return self.process_image(frame)

        h, w = frame.shape[:2]
        now_ms = int(time.perf_counter() * 1000)
        if now_ms <= self._last_ts:
            now_ms = self._last_ts + 1
        self._last_ts = now_ms
        timestamp_ms = now_ms

        inf_w, inf_h = self.inference_size
        if w > inf_w or h > inf_h:
            scale_f = min(inf_w / w, inf_h / h)
            nw = max(1, int(w * scale_f))
            nh = max(1, int(h * scale_f))
            small_frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        else:
            small_frame = frame
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        try:
            result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        except Exception as e:
            self._last_error = f"detect_for_video error: {e}"
            return self.process_image(frame)

        detected_hands: List[HandLandmarksData] = []
        if not result.hand_landmarks:
            self._prev_landmarks.clear()
            return detected_hands

        for idx, landmarks in enumerate(result.hand_landmarks):
            handedness = "Right"
            if result.handedness and idx < len(result.handedness):
                handedness = result.handedness[idx][0].category_name

            raw_norm = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)

            curr_pixels = np.zeros((21, 2), dtype=np.float32)
            curr_pixels[:, 0] = raw_norm[:, 0] * w
            curr_pixels[:, 1] = raw_norm[:, 1] * h

            if handedness in self._prev_landmarks:
                wrist_movement = float(np.linalg.norm(curr_pixels[0] - self._prev_landmarks[handedness][0]))
                if wrist_movement > 50.0:
                    smoothed_pixels = curr_pixels
                else:
                    alpha = self.smoothing_factor
                    smoothed_pixels = alpha * curr_pixels + (1.0 - alpha) * self._prev_landmarks[handedness]
            else:
                smoothed_pixels = curr_pixels
            self._prev_landmarks[handedness] = smoothed_pixels

            if result.hand_world_landmarks and idx < len(result.hand_world_landmarks):
                world_lm = np.array([[lm.x, lm.y, lm.z] for lm in result.hand_world_landmarks[idx]], dtype=np.float32)
            else:
                world_lm = raw_norm.copy()

            x_min = int(np.clip(np.min(smoothed_pixels[:, 0]) - 20, 0, w))
            y_min = int(np.clip(np.min(smoothed_pixels[:, 1]) - 20, 0, h))
            x_max = int(np.clip(np.max(smoothed_pixels[:, 0]) + 20, 0, w))
            y_max = int(np.clip(np.max(smoothed_pixels[:, 1]) + 20, 0, h))

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

        detected_hands.sort(key=lambda h: h.hand_scale, reverse=True)
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
            try:
                self.landmarker.close()
            except Exception:
                pass
        if hasattr(self, "image_landmarker") and self.image_landmarker:
            try:
                self.image_landmarker.close()
            except Exception:
                pass
