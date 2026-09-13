"""
Main Application Runner for OmniGesture AI Studio.
High-performance, low-latency threaded pipeline for silky-smooth responsiveness.
"""
from datetime import datetime
from enum import IntEnum
from pathlib import Path
import argparse
import os
import sys
import time

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ["GLOG_minloglevel"] = "3"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"

import cv2
import numpy as np

from config import AppConfig, SNAPSHOT_DIR
from camera_stream import ThreadedCamera
from hand_tracker import HandTracker
from gesture_recognizer import GestureRecognizer
from air_canvas import AirCanvas
from virtual_mouse import VirtualMouse
from hud_renderer import HUDRenderer
from rehab_tracker import RehabTracker


class StudioMode(IntEnum):
    HUD_ANALYTICS = 1
    AIR_CANVAS = 2
    VIRTUAL_MOUSE = 3
    REHAB_METRICS = 4


MODE_NAMES = {
    StudioMode.HUD_ANALYTICS: "HUD & Analytics",
    StudioMode.AIR_CANVAS: "Air Canvas (Drawing)",
    StudioMode.VIRTUAL_MOUSE: "Virtual Mouse",
    StudioMode.REHAB_METRICS: "Biometrics & Rehab",
}


def main():
    parser = argparse.ArgumentParser(description="OmniGesture AI Studio")
    parser.add_argument("--camera", type=int, default=AppConfig.camera.device_index, help="Camera index")
    parser.add_argument("--mode", type=int, default=1, choices=[1, 2, 3, 4], help="Initial mode (1-4)")
    args = parser.parse_args()

    print("=" * 60)
    print("  OMNIGESTURE AI STUDIO - Initializing...")
    print("=" * 60)

    print("[1/5] Loading Hand Landmarker model...")
    tracker = HandTracker(
        model_path=AppConfig.tracker.model_path,
        num_hands=AppConfig.tracker.num_hands,
        min_detection_confidence=AppConfig.tracker.min_hand_detection_confidence,
        min_tracking_confidence=AppConfig.tracker.min_tracking_confidence,
        smoothing_factor=AppConfig.tracker.smoothing_factor,
        inference_size=(AppConfig.tracker.inference_width, AppConfig.tracker.inference_height),
    )

    print("[2/5] Initializing Gesture Recognizer...")
    gesture_engine = GestureRecognizer()

    print("[3/5] Starting Zero-Latency Threaded Camera...")
    camera = ThreadedCamera(
        device_index=args.camera,
        width=AppConfig.camera.width,
        height=AppConfig.camera.height,
        target_fps=AppConfig.camera.target_fps,
    )

    # Wait for first valid frame
    actual_w, actual_h = AppConfig.camera.width, AppConfig.camera.height
    for _ in range(20):
        ret, frame = camera.read()
        if ret and frame is not None:
            actual_h, actual_w = frame.shape[:2]
            break
        time.sleep(0.05)

    print(f"      Camera active resolution: {actual_w}x{actual_h}")

    print("[4/5] Initializing Interactive Modules...")
    air_canvas = AirCanvas(width=actual_w, height=actual_h)
    virtual_mouse = VirtualMouse(camera_w=actual_w, camera_h=actual_h)
    hud = HUDRenderer(width=actual_w, height=actual_h)
    rehab = RehabTracker(width=actual_w, height=actual_h)

    current_mode = StudioMode(args.mode)
    print(f"[5/5] Ready! Active Mode: {MODE_NAMES[current_mode]}")
    print("=" * 60)
    print("CONTROLS:")
    print("  '1' - HUD & Analytics Mode")
    print("  '2' - Air Canvas Mode")
    print("  '3' - Virtual Mouse Mode")
    print("  '4' - Biometrics & Rehab Mode")
    print("  'c' - Clear Canvas | 'u' - Undo | 'b' - Toggle Whiteboard")
    print("  's' - Save Snapshot | 'm' - Toggle Mouse | 'h' - Help Guide")
    print("  'q' / ESC - Quit")
    print("=" * 60)

    window_name = "OmniGesture AI Studio"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, actual_w, actual_h)

    prev_time = time.time()
    fps_smooth = 30.0

    is_camera_paused = False
    frame_count = 0

    try:
        while True:
            frame_count += 1
            if is_camera_paused:
                standby_frame = np.zeros((actual_h, actual_w, 3), dtype=np.uint8)
                cv2.putText(
                    standby_frame,
                    "CAMERA OFF (STANDBY MODE)",
                    (actual_w // 2 - 200, actual_h // 2 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    AppConfig.colors.GOLD_YELLOW,
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    standby_frame,
                    "Webcam hardware is released. Press 'p' or SPACE to resume.",
                    (actual_w // 2 - 230, actual_h // 2 + 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (180, 180, 180),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow(window_name, standby_frame)
                k = cv2.waitKey(40) & 0xFF
                if k in [ord("q"), 27]:
                    break
                try:
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 0:
                        break
                except Exception:
                    pass
                if k in [ord("p"), 32]:
                    camera.resume()
                    is_camera_paused = False
                    hud.notify("Camera Resumed")
                continue

            ret, frame = camera.read()
            if not ret or frame is None:
                time.sleep(0.002)
                continue

            if AppConfig.camera.flip_horizontal:
                frame = cv2.flip(frame, 1)

            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt > 0:
                inst_fps = 1.0 / dt
                fps_smooth = 0.9 * fps_smooth + 0.1 * inst_fps

            # Process hand tracking with downscaled inference + full coordinate restore
            hands = tracker.process_frame(frame)
            gestures = [gesture_engine.recognize(hand) for hand in hands]

            primary_idx = 0
            for idx, h in enumerate(hands):
                if h.handedness == "Right":
                    primary_idx = idx
                    break

            # MODE-SPECIFIC LOGIC & RENDERING
            if current_mode == StudioMode.AIR_CANVAS:
                if hands:
                    status = air_canvas.update(hands[primary_idx], gestures[primary_idx])
                    if status:
                        hud.notify(status, duration=1.2)

                display_frame = air_canvas.render_composite(frame)

                if hands:
                    accent = air_canvas.current_color if not air_canvas.is_eraser else (200, 200, 200)
                    display_frame = hud.draw_skeleton(display_frame, hands[primary_idx], accent)

            elif current_mode == StudioMode.VIRTUAL_MOUSE:
                display_frame = frame.copy()
                cv2.rectangle(
                    display_frame,
                    (virtual_mouse.box_x1, virtual_mouse.box_y1),
                    (virtual_mouse.box_x2, virtual_mouse.box_y2),
                    (60, 60, 80),
                    1,
                    cv2.LINE_AA,
                )
                status_text = "MOUSE ACTIVE" if virtual_mouse.enabled else "MOUSE PAUSED (Press 'm' to toggle)"
                cv2.putText(
                    display_frame,
                    status_text,
                    (virtual_mouse.box_x1 + 10, virtual_mouse.box_y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    AppConfig.colors.EMERALD_GREEN if virtual_mouse.enabled else (140, 140, 140),
                    1,
                    cv2.LINE_AA,
                )

                if hands:
                    status = virtual_mouse.update(hands[primary_idx], gestures[primary_idx])
                    if status:
                        hud.notify(status, duration=1.0)
                    for hand in hands:
                        display_frame = hud.draw_skeleton(display_frame, hand, AppConfig.colors.CYAN)

            elif current_mode == StudioMode.REHAB_METRICS:
                display_frame = frame.copy()
                for idx, hand in enumerate(hands):
                    accent = AppConfig.colors.CYAN if hand.handedness == "Right" else AppConfig.colors.NEON_PINK
                    display_frame = hud.draw_skeleton(display_frame, hand, accent)
                display_frame = rehab.draw_rehab_dashboard(display_frame, hands, gestures)

            else:  # StudioMode.HUD_ANALYTICS (Default)
                display_frame = frame.copy()
                for idx, (hand, gesture) in enumerate(zip(hands, gestures)):
                    accent = AppConfig.colors.CYAN if hand.handedness == "Right" else AppConfig.colors.NEON_PINK
                    display_frame = hud.draw_skeleton(display_frame, hand, accent)
                    display_frame = hud.draw_bounding_box(display_frame, hand, gesture.name)
                    display_frame = hud.draw_gesture_card(display_frame, hand, gesture, slot_idx=idx)

            # COMMON HUD OVERLAYS
            display_frame = hud.draw_top_telemetry(display_frame, fps_smooth, MODE_NAMES[current_mode])

            if hud.show_help:
                display_frame = hud.draw_help_overlay(display_frame)

            # Display window
            cv2.imshow(window_name, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in [ord("q"), 27]:
                break
            elif key == ord("1"):
                current_mode = StudioMode.HUD_ANALYTICS
                hud.notify("Mode: HUD & Analytics")
            elif key == ord("2"):
                current_mode = StudioMode.AIR_CANVAS
                hud.notify("Mode: Air Canvas")
            elif key == ord("3"):
                current_mode = StudioMode.VIRTUAL_MOUSE
                virtual_mouse.enabled = True
                hud.notify("Mode: Virtual Mouse (Active)")
            elif key == ord("4"):
                current_mode = StudioMode.REHAB_METRICS
                hud.notify("Mode: Biometrics & Rehab")
            elif key == ord("c"):
                air_canvas.clear()
                hud.notify("Canvas Cleared")
            elif key == ord("u"):
                if air_canvas.undo():
                    hud.notify("Stroke Undone")
            elif key == ord("b"):
                air_canvas.whiteboard_mode = not air_canvas.whiteboard_mode
                hud.notify("Whiteboard Mode" if air_canvas.whiteboard_mode else "Camera Mode")
            elif key == ord("m"):
                state = virtual_mouse.toggle()
                hud.notify("Virtual Mouse ON" if state else "Virtual Mouse OFF")
            elif key == ord("h"):
                hud.show_help = not hud.show_help
            elif key == ord("s"):
                saved_path = SNAPSHOT_DIR / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                if current_mode == StudioMode.AIR_CANVAS:
                    saved_path = air_canvas.save_artwork()
                else:
                    cv2.imwrite(str(saved_path), display_frame)
                hud.notify(f"Saved: {saved_path.name}")
                print(f"[Snapshot] Saved to {saved_path}")
            elif key in [ord("p"), 32]:
                camera.pause()
                is_camera_paused = True
                print("[Camera] Camera paused & hardware released (webcam OFF).")

            # Check if user clicked the 'X' button to close the window
            if frame_count > 15:
                try:
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 0:
                        print("\n[OmniGesture] Window closed by user.")
                        break
                except Exception:
                    pass

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        camera.release()
        tracker.close()
        cv2.destroyAllWindows()
        print("Camera and tracker released.")
        sys.exit(0)


if __name__ == "__main__":
    main()
