"""
Camera & MediaPipe Diagnostic Script.
Verifies camera device access, resolution, and MediaPipe hand landmark detection.
"""
from pathlib import Path
import sys
import time
import cv2

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import detection_settings
from services.hand_detector import HandDetector


def main():
    print("=" * 60)
    print("  OMNIGESTURE AI // CAMERA & TRACKING DIAGNOSTIC")
    print("=" * 60)

    device_idx = 0
    print(f"[*] Opening webcam index {device_idx} with DirectShow...")
    cap = cv2.VideoCapture(device_idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(device_idx)

    if not cap.isOpened():
        print(f"[!] Error: Could not open camera {device_idx}.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[OK] Camera opened successfully at {w}x{h}.")

    print("[*] Loading MediaPipe Hand Landmarker model...")
    detector = HandDetector()
    print("[OK] MediaPipe loaded.")

    print("\nRunning diagnostic test loop for 5 seconds...")
    start_time = time.time()
    frames_processed = 0

    while time.time() - start_time < 5.0:
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        frames_processed += 1
        hands = detector.process_frame(frame)
        if hands:
            print(f"  Frame {frames_processed}: Detected {len(hands)} hand(s) - Primary: {hands[0].handedness}")

    fps = frames_processed / (time.time() - start_time)
    print(f"\n[OK] Diagnostic complete! Average Camera FPS: {fps:.1f}")

    detector.close()
    cap.release()
    print("[OK] Camera hardware released cleanly.")


if __name__ == "__main__":
    main()
