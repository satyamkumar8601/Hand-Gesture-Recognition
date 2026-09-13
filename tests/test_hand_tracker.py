"""
Integration test for HandTracker with real MediaPipe HandLandmarker.
"""
from pathlib import Path
import sys
import unittest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
from config import AppConfig
from hand_tracker import HandTracker


class TestHandTrackerIntegration(unittest.TestCase):
    def test_tracker_initialization_and_empty_frame(self):
        tracker = HandTracker(
            model_path=AppConfig.tracker.model_path,
            num_hands=2,
        )
        # Create blank test frame (720, 1280, 3)
        blank_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        hands = tracker.process_frame(blank_frame)

        # No hands should be detected in blank black frame
        self.assertIsInstance(hands, list)
        self.assertEqual(len(hands), 0)

        tracker.close()


if __name__ == "__main__":
    unittest.main()
