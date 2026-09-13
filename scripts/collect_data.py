"""
CLI Dataset Collection Tool for Gesture Landmarks.
Allows manual and continuous landmark sample recording for any gesture.
"""
from pathlib import Path
import sys
import time
import cv2
import pandas as pd
import numpy as np

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import DATASET_FILE, DATASET_DIR, ALL_GESTURES
from services.hand_detector import HandDetector
from ml.feature_extractor import FeatureExtractor


def main():
    print("=" * 60)
    print("  OMNIGESTURE AI // CLI DATASET COLLECTION STUDIO")
    print("=" * 60)
    print("\nSupported Gestures:")
    for idx, g in enumerate(ALL_GESTURES, 1):
        print(f"  [{idx:2d}] {g}")

    choice = input("\nEnter gesture number (or name): ").strip()
    selected_gesture = None
    if choice.isdigit() and 1 <= int(choice) <= len(ALL_GESTURES):
        selected_gesture = ALL_GESTURES[int(choice) - 1]
    elif choice in ALL_GESTURES:
        selected_gesture = choice
    else:
        print("[!] Invalid gesture selection.")
        return

    print(f"\n[Selected Gesture]: {selected_gesture}")
    target_count = input("Target samples to capture [Default 100]: ").strip()
    target_count = int(target_count) if target_count.isdigit() else 100

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[!] Error: Could not open camera.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    detector = HandDetector()
    feature_names = FeatureExtractor.get_feature_names()

    collected = 0
    capturing = False
    window_name = f"Dataset Collector - {selected_gesture}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print("\nCONTROLS:")
    print("  SPACE - Toggle continuous recording ON / OFF")
    print("  'c'   - Capture single sample")
    print("  'q'   - Finish and save")

    captured_rows = []

    try:
        while collected < target_count:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            frame = cv2.flip(frame, 1)
            hands = detector.process_frame(frame)
            display = detector.draw_landmarks(frame, hands)

            # Auto or manual capture
            should_save = False
            key = cv2.waitKey(1) & 0xFF
            if key in [ord("q"), 27]:
                break
            elif key == 32:  # Space
                capturing = not capturing
            elif key == ord("c"):
                should_save = True

            if (capturing or should_save) and hands:
                primary = hands[0]
                feat = FeatureExtractor.extract_features(primary.landmarks_pixel, primary.landmarks_world, primary.handedness)
                row_dict = {k: float(v) for k, v in zip(feature_names, feat)}
                row_dict["label"] = selected_gesture
                captured_rows.append(row_dict)
                collected += 1
                time.sleep(0.04)  # ~25 samples per second

            # Overlay HUD
            cv2.rectangle(display, (10, 10), (320, 75), (20, 20, 26), -1)
            cv2.rectangle(display, (10, 10), (320, 75), (60, 60, 80), 1)
            status_text = "RECORDING" if capturing else "PAUSED (Press SPACE)"
            status_color = (0, 235, 255) if capturing else (160, 160, 160)
            cv2.putText(display, f"Gesture: {selected_gesture}", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(display, f"Status: {status_text}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 1, cv2.LINE_AA)
            cv2.putText(display, f"Progress: {collected} / {target_count}", (20, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120), 1, cv2.LINE_AA)

            cv2.imshow(window_name, display)
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

    finally:
        cap.release()
        detector.close()
        cv2.destroyAllWindows()

    if captured_rows:
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        file_exists = DATASET_FILE.exists()
        df_new = pd.DataFrame(captured_rows)
        df_new.to_csv(DATASET_FILE, mode="a", header=not file_exists, index=False)
        print(f"\n[OK] Successfully saved {len(captured_rows)} samples of '{selected_gesture}' to {DATASET_FILE}.")
    else:
        print("\nNo samples captured.")


if __name__ == "__main__":
    main()
