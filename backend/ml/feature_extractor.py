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
        Uses scale-normalized distance and joint relative geometry invariant to hand rotation.
        """
        pts = landmarks_pixel
        wrist = pts[0]
        middle_mcp = pts[9]
        scale = max(float(np.linalg.norm(middle_mcp - wrist)), 1.0)

        def is_finger_open(tip_idx: int, pip_idx: int, mcp_idx: int) -> bool:
            tip = pts[tip_idx]
            pip = pts[pip_idx]
            mcp = pts[mcp_idx]

            d_tip_wrist = np.linalg.norm(tip - wrist)
            d_pip_wrist = np.linalg.norm(pip - wrist)
            d_tip_mcp = np.linalg.norm(tip - mcp)
            d_pip_mcp = np.linalg.norm(pip - mcp)

            # Anatomical extension check:
            # 1. Rotation-invariant: tip must be significantly further from MCP knuckle than PIP is
            is_mcp_extended = d_tip_mcp > (d_pip_mcp * 1.12)
            # 2. Tip extended away from wrist or higher than PIP in image coordinates
            is_wrist_extended = d_tip_wrist > (d_pip_wrist * 1.03)
            is_upright = tip[1] < pip[1]

            return bool(is_mcp_extended and (is_wrist_extended or is_upright))

        index_open = is_finger_open(8, 6, 5)
        middle_open = is_finger_open(12, 10, 9)
        ring_open = is_finger_open(16, 14, 13)
        pinky_open = is_finger_open(20, 18, 17)

        # Thumb: invariant extension using distance to MCP and opposite side of palm (pinky MCP)
        thumb_tip = pts[4]
        thumb_ip = pts[3]
        thumb_mcp = pts[2]
        index_mcp = pts[5]
        pinky_mcp = pts[17]

        d_tip_mcp = np.linalg.norm(thumb_tip - thumb_mcp)
        d_ip_mcp = np.linalg.norm(thumb_ip - thumb_mcp)
        d_tip_index = np.linalg.norm(thumb_tip - index_mcp) / scale
        d_tip_pinky = np.linalg.norm(thumb_tip - pinky_mcp) / scale

        # Invariant thumb check + lateral separation
        thumb_open = (d_tip_index > 0.30 and d_tip_pinky > 0.45 and d_tip_mcp > d_ip_mcp * 1.05)

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
