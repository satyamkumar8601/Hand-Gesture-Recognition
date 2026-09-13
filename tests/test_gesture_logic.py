"""
Unit tests for OmniGesture AI Studio.
Tests geometric math, gesture recognition, state transitions, air canvas, and tracker.
"""
from pathlib import Path
import sys
import unittest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np

from gesture_recognizer import (
    compute_angle_3points,
    GestureRecognizer,
    FingerStates,
    DynamicMotionTracker,
)
from hand_tracker import (
    HandData,
    WRIST,
    THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP,
    INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP,
    MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP,
    RING_MCP, RING_PIP, RING_DIP, RING_TIP,
    PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP,
)
from air_canvas import AirCanvas
from virtual_mouse import VirtualMouse


def create_synthetic_hand(
    extended_fingers: list[bool],  # [thumb, index, middle, ring, pinky]
    pinch: bool = False,
    handedness: str = "Right",
) -> HandData:
    """Helper to synthesize 21 3D landmarks representing specific hand configurations."""
    lm = np.zeros((21, 3), dtype=np.float32)

    # Wrist at center bottom
    lm[WRIST] = [0.5, 0.8, 0.0]

    # Base MCP positions across palm
    lm[INDEX_MCP] = [0.45, 0.55, 0.0]
    lm[MIDDLE_MCP] = [0.50, 0.50, 0.0]
    lm[RING_MCP] = [0.55, 0.52, 0.0]
    lm[PINKY_MCP] = [0.60, 0.56, 0.0]

    # Thumb base
    lm[THUMB_CMC] = [0.40, 0.70, 0.0]
    lm[THUMB_MCP] = [0.35, 0.65, 0.0]

    # Set finger joints based on extended state
    finger_joints = [
        (0, [THUMB_IP, THUMB_TIP]),
        (1, [INDEX_PIP, INDEX_DIP, INDEX_TIP]),
        (2, [MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP]),
        (3, [RING_PIP, RING_DIP, RING_TIP]),
        (4, [PINKY_PIP, PINKY_DIP, PINKY_TIP]),
    ]

    for f_idx, joints in finger_joints:
        is_ext = extended_fingers[f_idx]
        if f_idx == 0:  # Thumb
            if is_ext:
                lm[THUMB_IP] = [0.30, 0.58, 0.0]
                lm[THUMB_TIP] = [0.24, 0.50, 0.0]
            else:
                lm[THUMB_IP] = [0.38, 0.62, 0.0]
                lm[THUMB_TIP] = [0.42, 0.60, 0.0]  # Tucked against palm
        else:
            mcp_idx = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP][f_idx - 1]
            base_x = lm[mcp_idx, 0]
            base_y = lm[mcp_idx, 1]

            if is_ext:
                # Extending upward away from wrist
                lm[joints[0]] = [base_x, base_y - 0.10, 0.0]
                lm[joints[1]] = [base_x, base_y - 0.18, 0.0]
                lm[joints[2]] = [base_x, base_y - 0.26, 0.0]
            else:
                # Curled downward toward wrist
                lm[joints[0]] = [base_x, base_y + 0.04, 0.0]
                lm[joints[1]] = [base_x, base_y + 0.08, 0.0]
                lm[joints[2]] = [base_x, base_y + 0.12, 0.0]

    if pinch:
        # Move thumb tip to index tip
        lm[THUMB_TIP] = lm[INDEX_TIP].copy() + [0.01, 0.01, 0.0]

    # Pixel coords (assuming 1280x720)
    px = np.column_stack((lm[:, 0] * 1280, lm[:, 1] * 720)).astype(np.int32)
    hand_size = float(np.linalg.norm(lm[MIDDLE_MCP, :2] - lm[WRIST, :2]))

    return HandData(
        handedness=handedness,
        handedness_score=0.98,
        landmarks_norm=lm,
        landmarks_pixel=px,
        bbox=(200, 100, 800, 700),
        hand_size=hand_size,
        palm_center=(640, 450),
    )


class TestGeometryMath(unittest.TestCase):
    def test_compute_angle_right_angle(self):
        p1 = np.array([0.0, 1.0])
        p2 = np.array([0.0, 0.0])
        p3 = np.array([1.0, 0.0])
        angle = compute_angle_3points(p1, p2, p3)
        self.assertAlmostEqual(angle, 90.0, places=3)

    def test_compute_angle_straight_line(self):
        p1 = np.array([-1.0, 0.0])
        p2 = np.array([0.0, 0.0])
        p3 = np.array([1.0, 0.0])
        angle = compute_angle_3points(p1, p2, p3)
        self.assertAlmostEqual(angle, 180.0, places=3)


class TestGestureRecognition(unittest.TestCase):
    def setUp(self):
        self.recognizer = GestureRecognizer()

    def test_open_palm(self):
        hand = create_synthetic_hand([True, True, True, True, True])
        result = self.recognizer.recognize(hand)
        self.assertEqual(result.name, "OPEN_PALM")
        self.assertEqual(result.finger_states.count_extended, 5)

    def test_fist(self):
        hand = create_synthetic_hand([False, False, False, False, False])
        result = self.recognizer.recognize(hand)
        self.assertEqual(result.name, "FIST")
        self.assertEqual(result.finger_states.count_extended, 0)

    def test_victory(self):
        hand = create_synthetic_hand([False, True, True, False, False])
        result = self.recognizer.recognize(hand)
        self.assertIn(result.name, ["VICTORY", "PEACE"])
        self.assertTrue(result.finger_states.index)
        self.assertTrue(result.finger_states.middle)
        self.assertFalse(result.finger_states.ring)

    def test_pointing(self):
        hand = create_synthetic_hand([False, True, False, False, False])
        result = self.recognizer.recognize(hand)
        self.assertIn("POINTING", result.name)

    def test_pinch_detection(self):
        hand = create_synthetic_hand([True, True, False, False, False], pinch=True)
        result = self.recognizer.recognize(hand)
        self.assertTrue(result.is_pinch)


class TestAirCanvas(unittest.TestCase):
    def setUp(self):
        self.canvas = AirCanvas(width=1280, height=720)

    def test_palette_initialization(self):
        self.assertGreater(len(self.canvas.palette_items), 5)
        names = [item.name for item in self.canvas.palette_items]
        self.assertIn("Cyan", names)
        self.assertIn("Eraser", names)
        self.assertIn("Clear All", names)
        self.assertIn("Undo", names)

    def test_drawing_and_undo(self):
        hand = create_synthetic_hand([False, True, False, False, False])
        recognizer = GestureRecognizer()
        gesture = recognizer.recognize(hand)

        # First update initializes prev_point
        self.canvas.update(hand, gesture)
        # Move hand slightly and update to draw stroke
        hand.landmarks_pixel[INDEX_TIP] += [10, 10]
        self.canvas.update(hand, gesture)

        # Verify pixels were drawn
        self.assertTrue(np.any(self.canvas.canvas > 0))

        # Test Undo
        undone = self.canvas.undo()
        self.assertTrue(undone)

        # Test Clear
        self.canvas.clear()
        self.assertEqual(np.count_nonzero(self.canvas.canvas), 0)


class TestVirtualMouse(unittest.TestCase):
    def test_boundary_mapping(self):
        vm = VirtualMouse(camera_w=1280, camera_h=720)
        self.assertGreater(vm.box_x2, vm.box_x1)
        self.assertGreater(vm.box_y2, vm.box_y1)
        # Toggle test
        state1 = vm.toggle()
        self.assertTrue(state1)
        state2 = vm.toggle()
        self.assertFalse(state2)


if __name__ == "__main__":
    unittest.main()
