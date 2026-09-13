"""
Scale-Invariant & Translation-Invariant Feature Extraction for 3D Hand Landmarks.
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple
import numpy as np


@dataclass
class FingerStates:
    thumb: bool
    index: bool
    middle: bool
    ring: bool
    pinky: bool

    def as_dict(self) -> Dict[str, bool]:
        return {
            "thumb": self.thumb,
            "index": self.index,
            "middle": self.middle,
            "ring": self.ring,
            "pinky": self.pinky,
        }

    def count_extended(self) -> int:
        return sum([self.thumb, self.index, self.middle, self.ring, self.pinky])


class FeatureExtractor:
    """
    Transforms raw (21, 3) landmarks into a normalized, scale-invariant
    feature vector suitable for machine learning classification.
    """

    FEATURE_NAMES: List[str] = []

    @classmethod
    def get_feature_names(cls) -> List[str]:
        if cls.FEATURE_NAMES:
            return cls.FEATURE_NAMES

        names = []
        # 21 relative 3D coords = 63
        for i in range(21):
            names.extend([f"rel_x_{i}", f"rel_y_{i}", f"rel_z_{i}"])

        # Tip to wrist distances (5)
        for finger in ["thumb", "index", "middle", "ring", "pinky"]:
            names.append(f"dist_wrist_tip_{finger}")

        # Tip to MCP distances (5)
        for finger in ["thumb", "index", "middle", "ring", "pinky"]:
            names.append(f"dist_mcp_tip_{finger}")

        # Adjacent finger tip distances (4)
        names.extend(["dist_thumb_index", "dist_index_middle", "dist_middle_ring", "dist_ring_pinky"])

        # Finger extension states (5)
        for finger in ["thumb", "index", "middle", "ring", "pinky"]:
            names.append(f"is_open_{finger}")

        cls.FEATURE_NAMES = names
        return names

    @staticmethod
    def extract_finger_states(landmarks_pixel: np.ndarray, handedness: str = "Right") -> FingerStates:
        """
        Determine whether each of the 5 fingers is open/extended or closed/curled.
        Uses scale-normalized distance and joint relative geometry.
        """
        pts = landmarks_pixel
        wrist = pts[0]
        middle_mcp = pts[9]
        scale = max(float(np.linalg.norm(middle_mcp - wrist)), 1.0)

        # Non-thumb fingers: tip y vs pip y, and distance from wrist to tip vs wrist to pip
        index_open = (np.linalg.norm(pts[8] - wrist) > np.linalg.norm(pts[6] - wrist) * 1.05) and (pts[8][1] < pts[6][1] + scale * 0.15)
        middle_open = (np.linalg.norm(pts[12] - wrist) > np.linalg.norm(pts[10] - wrist) * 1.05) and (pts[12][1] < pts[10][1] + scale * 0.15)
        ring_open = (np.linalg.norm(pts[16] - wrist) > np.linalg.norm(pts[14] - wrist) * 1.05) and (pts[16][1] < pts[14][1] + scale * 0.15)
        pinky_open = (np.linalg.norm(pts[20] - wrist) > np.linalg.norm(pts[18] - wrist) * 1.05) and (pts[20][1] < pts[18][1] + scale * 0.15)

        # Thumb: lateral extension relative to IP joint and palm width
        thumb_tip = pts[4]
        thumb_ip = pts[3]
        thumb_mcp = pts[2]
        index_mcp = pts[5]

        # Horizontal separation from Index MCP
        if handedness == "Right":
            thumb_open = thumb_tip[0] < thumb_ip[0] and (np.linalg.norm(thumb_tip - index_mcp) / scale > 0.45)
        else:
            thumb_open = thumb_tip[0] > thumb_ip[0] and (np.linalg.norm(thumb_tip - index_mcp) / scale > 0.45)

        return FingerStates(
            thumb=bool(thumb_open),
            index=bool(index_open),
            middle=bool(middle_open),
            ring=bool(ring_open),
            pinky=bool(pinky_open),
        )

    @classmethod
    def extract_features(cls, landmarks_pixel: np.ndarray, world_landmarks: np.ndarray, handedness: str = "Right") -> np.ndarray:
        """
        Compute full 82-dimensional feature vector.
        """
        pts = landmarks_pixel
        wrist = pts[0]
        middle_mcp = pts[9]
        scale = max(float(np.linalg.norm(middle_mcp - wrist)), 1.0)

        features: List[float] = []

        # 1. 21 normalized 3D coordinates relative to wrist (63 values)
        # Using world landmarks for 3D depth and pixel coords for 2D position
        wrist_3d = world_landmarks[0]
        for i in range(21):
            diff = (world_landmarks[i] - wrist_3d)
            features.extend([float(diff[0]), float(diff[1]), float(diff[2])])

        # 2. Tip to wrist distances (5 values, normalized by scale)
        tips = [4, 8, 12, 16, 20]
        for tip in tips:
            dist = float(np.linalg.norm(pts[tip] - wrist) / scale)
            features.append(dist)

        # 3. Tip to MCP distances (5 values)
        mcps = [2, 5, 9, 13, 17]
        for tip, mcp in zip(tips, mcps):
            dist = float(np.linalg.norm(pts[tip] - pts[mcp]) / scale)
            features.append(dist)

        # 4. Adjacent fingertip distances (4 values)
        features.append(float(np.linalg.norm(pts[4] - pts[8]) / scale))   # Thumb - Index (Pinch)
        features.append(float(np.linalg.norm(pts[8] - pts[12]) / scale))  # Index - Middle
        features.append(float(np.linalg.norm(pts[12] - pts[16]) / scale)) # Middle - Ring
        features.append(float(np.linalg.norm(pts[16] - pts[20]) / scale)) # Ring - Pinky

        # 5. Finger extension states (5 binary values)
        states = cls.extract_finger_states(pts, handedness)
        features.extend([
            1.0 if states.thumb else 0.0,
            1.0 if states.index else 0.0,
            1.0 if states.middle else 0.0,
            1.0 if states.ring else 0.0,
            1.0 if states.pinky else 0.0,
        ])

        return np.array(features, dtype=np.float32)
