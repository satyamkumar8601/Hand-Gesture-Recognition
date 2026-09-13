"""
Hybrid Gesture Recognition Engine: Rule-Based Heuristics + Machine Learning Classifier.
"""
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional
import numpy as np

try:
    from backend.config import ALL_GESTURES, GESTURE_ICONS
    from backend.ml.feature_extractor import FeatureExtractor, FingerStates
    from backend.ml.model_loader import ModelLoader
    from backend.services.hand_detector import HandLandmarksData
except ImportError:
    from config import ALL_GESTURES, GESTURE_ICONS
    from ml.feature_extractor import FeatureExtractor, FingerStates
    from ml.model_loader import ModelLoader
    from services.hand_detector import HandLandmarksData


@dataclass
class GestureResult:
    name: str
    confidence: float
    finger_states: FingerStates
    is_ml: bool
    handedness: str
    icon: str
    probabilities: Dict[str, float]
    pinch_distance_ratio: float = 0.0
    is_pinch: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "confidence": round(self.confidence * 100, 1),
            "finger_states": self.finger_states.as_dict(),
            "is_ml": self.is_ml,
            "handedness": self.handedness,
            "icon": self.icon,
            "extended_count": self.finger_states.count_extended(),
            "probabilities": self.probabilities,
            "pinch_distance_ratio": round(self.pinch_distance_ratio, 3),
            "is_pinch": self.is_pinch,
        }


class GestureDetector:
    def __init__(self, min_confidence: float = 0.50):
        self.min_confidence = min_confidence
        self.model_loader = ModelLoader.get_instance()

    def recognize(self, hand: HandLandmarksData) -> GestureResult:
        """
        Classify gesture using ML model if available; otherwise use rule-based heuristics.
        """
        pts = hand.landmarks_pixel
        world_pts = hand.landmarks_world
        handedness = hand.handedness
        scale = max(hand.hand_scale, 1e-4)

        finger_states = FeatureExtractor.extract_finger_states(pts, handedness)
        extended_count = finger_states.count_extended()

        # Compute pinch distance ratio between thumb tip (4) and index tip (8)
        pinch_dist = float(np.linalg.norm(pts[4] - pts[8]))
        pinch_ratio = float(pinch_dist / scale)
        is_pinch = pinch_ratio < 0.28

        # Try ML Prediction first
        if self.model_loader.is_loaded:
            feat_vec = FeatureExtractor.extract_features(pts, world_pts, handedness)
            pred_gesture, conf, probs = self.model_loader.predict(feat_vec)

            if conf >= self.min_confidence and pred_gesture != "Unknown":
                icon = GESTURE_ICONS.get(pred_gesture, "✨")
                return GestureResult(
                    name=pred_gesture,
                    confidence=conf,
                    finger_states=finger_states,
                    is_ml=True,
                    handedness=handedness,
                    icon=icon,
                    probabilities=probs,
                    pinch_distance_ratio=pinch_ratio,
                    is_pinch=is_pinch,
                )

        # Rule-Based Heuristic Fallback (Demo Mode / Guaranteed Working)
        rule_gesture, rule_conf = self._rule_based_classify(hand, finger_states, extended_count)
        icon = GESTURE_ICONS.get(rule_gesture, "✨")

        return GestureResult(
            name=rule_gesture,
            confidence=rule_conf,
            finger_states=finger_states,
            is_ml=False,
            handedness=handedness,
            icon=icon,
            probabilities={rule_gesture: rule_conf},
            pinch_distance_ratio=pinch_ratio,
            is_pinch=is_pinch,
        )

    def _rule_based_classify(self, hand: HandLandmarksData, f: FingerStates, ext_count: int) -> Tuple[str, float]:
        """Geometric classification rules for all 17 gestures."""
        pts = hand.landmarks_pixel
        scale = hand.hand_scale
        wrist = pts[0]

        # 1. OK Sign: Thumb tip touches index tip, while middle, ring, pinky are extended
        pinch_dist = np.linalg.norm(pts[4] - pts[8]) / scale
        if pinch_dist < 0.28 and f.middle and f.ring:
            return "OK Sign", 0.96

        # 2. Fist: 0 fingers extended
        if ext_count == 0:
            return "Fist", 0.98

        # 3. Thumbs Up / Down: Only thumb extended, check vertical orientation
        if f.thumb and not (f.index or f.middle or f.ring or f.pinky):
            thumb_vec_y = pts[4][1] - pts[2][1]
            if thumb_vec_y < -scale * 0.35:
                return "Thumbs Up", 0.97
            elif thumb_vec_y > scale * 0.35:
                return "Thumbs Down", 0.96

        # 4. Victory / Peace / Two Fingers: Index & Middle open, others closed
        if f.index and f.middle and not (f.ring or f.pinky):
            separation = np.linalg.norm(pts[8] - pts[12]) / scale
            if separation > 0.35:
                return "Victory", 0.97
            return "Two Fingers", 0.94

        # 5. One Finger / Pointing: Only Index open
        if f.index and not (f.middle or f.ring or f.pinky):
            # Check horizontal pointing direction
            dx = pts[8][0] - pts[5][0]
            dy = pts[8][1] - pts[5][1]
            if abs(dx) > abs(dy) * 1.4:
                return ("Point Right" if dx > 0 else "Point Left"), 0.95
            return "One Finger", 0.96

        # 6. Three Fingers: Index, Middle, Ring open
        if f.index and f.middle and f.ring and not f.pinky and not f.thumb:
            return "Three Fingers", 0.95

        # 7. Four Fingers: Index, Middle, Ring, Pinky open, thumb tucked
        if f.index and f.middle and f.ring and f.pinky and not f.thumb:
            return "Four Fingers", 0.96

        # 8. Open Palm / Stop / Five Fingers: All 5 open
        if ext_count == 5:
            # Palm facing camera
            return "Open Palm", 0.98

        # 9. Rock Sign: Index and Pinky extended, Middle and Ring curled
        if f.index and f.pinky and not (f.middle or f.ring):
            return "Rock Sign", 0.96

        # 10. Call Me: Thumb and Pinky extended, other 3 curled
        if f.thumb and f.pinky and not (f.index or f.middle or f.ring):
            return "Call Me", 0.95

        # Generic based on finger count
        if ext_count == 1:
            return "One Finger", 0.85
        elif ext_count == 2:
            return "Two Fingers", 0.85
        elif ext_count == 3:
            return "Three Fingers", 0.85
        elif ext_count == 4:
            return "Four Fingers", 0.88
        elif ext_count >= 5:
            return "Five Fingers", 0.90

        return "Unknown", 0.50
