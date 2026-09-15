"""
Threaded Camera Stream Manager with Automatic Hardware Release.
Ensures webcam turns off immediately when not in active use.
"""
from typing import Optional, Tuple
import threading
import time
import cv2
import numpy as np

try:
    from backend.config import camera_settings
except ImportError:
    from config import camera_settings


class CameraService:
    _instance: Optional["CameraService"] = None

    def __init__(self, device_index: int = camera_settings.device_index, width: int = camera_settings.width, height: int = camera_settings.height):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps_limit = camera_settings.fps_limit

        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.lock = threading.Lock()
        self.ret = False
        self.frame: Optional[np.ndarray] = None
        self.thread: Optional[threading.Thread] = None

        self.active_subscribers = 0
        self.last_access_time = time.time()
        self.frame_id = 0
        self._hw_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "CameraService":
        if cls._instance is None:
            cls._instance = CameraService()
        return cls._instance

    def _safe_open_capture(self, index: int) -> Optional[cv2.VideoCapture]:
        """Try opening camera using DirectShow first, then standard backend, safely catching C++ errors."""
        cap = None
        # 1. Try DirectShow
        try:
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cap is not None and cap.isOpened():
                return cap
            if cap is not None:
                cap.release()
        except Exception as e:
            print(f"[CameraService] DirectShow open error on index {index}: {e}")
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

        # 2. Try Default Backend (MSMF / V4L)
        try:
            cap = cv2.VideoCapture(index)
            if cap is not None and cap.isOpened():
                return cap
            if cap is not None:
                cap.release()
        except Exception as e:
            print(f"[CameraService] Default backend open error on index {index}: {e}")
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

        return None

    def start(self) -> bool:
        """Start or resume the camera hardware capture with full exception safety."""
        with self._hw_lock:
            with self.lock:
                if self.running and self.cap is not None and self.cap.isOpened():
                    self.last_access_time = time.time()
                    return True

            # Attempt primary device index, then alternate fallback index
            indices_to_try = [self.device_index]
            alt_idx = 1 if self.device_index == 0 else 0
            if alt_idx not in indices_to_try:
                indices_to_try.append(alt_idx)

            cap = None
            successful_idx = self.device_index
            for idx in indices_to_try:
                cap = self._safe_open_capture(idx)
                if cap is not None and cap.isOpened():
                    successful_idx = idx
                    break
                time.sleep(0.1)

            if cap is None or not cap.isOpened():
                print(f"[CameraService Warning] Unable to open camera on indices {indices_to_try}.")
                return self._start_simulated_cloud_feed()

            # Configure properties safely (certain drivers crash if properties are set unsupported)
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            except Exception:
                pass

            try:
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            except Exception:
                pass

            try:
                cap.set(cv2.CAP_PROP_FPS, self.fps_limit)
            except Exception:
                pass

            # Warmup loop: DirectShow drivers often need several warmup frames to settle auto-exposure
            first_frame = None
            for _ in range(20):
                try:
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        first_frame = frame
                        break
                except Exception:
                    pass
                time.sleep(0.04)

            if first_frame is None:
                print(f"[CameraService Error] Camera opened at index {successful_idx} but produced no readable frames.")
                try:
                    cap.release()
                except Exception:
                    pass
                return False

            with self.lock:
                self.device_index = successful_idx
                self.cap = cap
                self.frame = first_frame
                self.ret = True
                self.frame_id += 1
                self.running = True
                self.last_access_time = time.time()

                self.thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.thread.start()

            print(f"[CameraService] Webcam {successful_idx} active ({first_frame.shape[1]}x{first_frame.shape[0]}).")
            return True

    def _capture_loop(self):
        """Dedicated background loop continuously reading freshest frame directly from camera sensor with zero buffer lag."""
        while self.running:
            if self.cap is None:
                break

            # Inactivity watchdog: auto-release if no subscribers are active AND no frames read for > 15s
            if self.active_subscribers == 0 and (time.time() - self.last_access_time > 15.0):
                print("[CameraService Watchdog] Inactivity detected (>15s, 0 subscribers). Powering down camera hardware.")
                threading.Thread(target=self.stop, daemon=True).start()
                break

            try:
                if self.cap is not None:
                    # cap.read() blocks naturally until hardware delivers next frame (~30-60 FPS)
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        with self.lock:
                            self.ret = True
                            self.frame = frame
                            self.frame_id += 1
                    else:
                        time.sleep(0.005)
            except Exception:
                time.sleep(0.01)

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Fetch the freshest frame with zero queue delay."""
        self.last_access_time = time.time()
        with self.lock:
            if not self.running or not self.ret or self.frame is None:
                return False, None
            return True, self.frame.copy()

    def read_frame_with_id(self) -> Tuple[bool, Optional[np.ndarray], int]:
        """Fetch frame with monotonic frame_id for caching and zero redundant inference."""
        self.last_access_time = time.time()
        with self.lock:
            if not self.running or not self.ret or self.frame is None:
                return False, None, self.frame_id
            return True, self.frame.copy(), self.frame_id

    def stop(self):
        """Release camera hardware completely and safely under hardware lock."""
        with self._hw_lock:
            cap_to_release = None
            thread_to_join = None

            with self.lock:
                if not self.running and self.cap is None:
                    return
                self.running = False
                cap_to_release = self.cap
                self.cap = None
                self.frame = None
                self.ret = False
                self.active_subscribers = 0
                thread_to_join = self.thread
                self.thread = None

            # Join capture loop thread before releasing capture handle
            current_thread = threading.current_thread()
            if thread_to_join is not None and thread_to_join.is_alive() and thread_to_join != current_thread:
                thread_to_join.join(timeout=0.5)

            if cap_to_release is not None:
                try:
                    cap_to_release.release()
                except Exception as e:
                    print(f"[CameraService] Exception releasing camera capture: {e}")
                # Windows DirectShow needs a small breather to free COM hardware lock
                time.sleep(0.1)
                print("[CameraService] Camera released & hardware turned OFF.")

    def _create_cloud_standby_frame(self, t: float) -> np.ndarray:
        h, w = self.height, self.width
        frame = np.full((h, w, 3), 20, dtype=np.uint8)
        # Subtle grid
        frame[::40, :] = np.clip(frame[::40, :] + 10, 0, 255)
        frame[:, ::40] = np.clip(frame[:, ::40, :] + 10, 0, 255)

        # Center card
        cw, ch = min(540, w - 30), min(230, h - 30)
        cx1 = max(0, (w - cw) // 2)
        cy1 = max(0, (h - ch) // 2)
        cv2.rectangle(frame, (cx1, cy1), (cx1 + cw, cy1 + ch), (30, 28, 38), -1)
        cv2.rectangle(frame, (cx1, cy1), (cx1 + cw, cy1 + ch), (241, 102, 99), 2)

        # Title
        cv2.putText(frame, "OMNIGESTURE CLOUD SERVER", (cx1 + 20, cy1 + 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)

        # Pulsing dot
        pulse = int(140 + 115 * np.sin(t * 3.5))
        cv2.circle(frame, (cx1 + 30, cy1 + 78), 7, (94, 197, pulse), -1, cv2.LINE_AA)
        cv2.putText(frame, "Cloud Server Active (Render / Headless)", (cx1 + 48, cy1 + 84),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (94, 197, 34), 1, cv2.LINE_AA)

        # Information
        cv2.putText(frame, "No physical webcam attached in cloud VM.", (cx1 + 20, cy1 + 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, "Run locally for USB webcam or use Web API endpoints.", (cx1 + 20, cy1 + 148),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (160, 160, 160), 1, cv2.LINE_AA)

        # Live timestamp
        time_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(t))
        cv2.putText(frame, time_str, (cx1 + 20, cy1 + 190),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 235, 0), 1, cv2.LINE_AA)
        return frame

    def _simulated_cloud_loop(self):
        while self.running:
            now = time.time()
            frame = self._create_cloud_standby_frame(now)
            with self.lock:
                self.frame = frame
                self.ret = True
                self.frame_id += 1
            time.sleep(0.066)  # ~15 FPS

    def _start_simulated_cloud_feed(self) -> bool:
        print("[CameraService] No physical camera found. Starting simulated cloud standby feed.")
        first_frame = self._create_cloud_standby_frame(time.time())
        with self.lock:
            self.cap = None
            self.frame = first_frame
            self.ret = True
            self.frame_id += 1
            self.running = True
            self.last_access_time = time.time()
            self.thread = threading.Thread(target=self._simulated_cloud_loop, daemon=True)
            self.thread.start()
        return True

    def add_subscriber(self):
        self.last_access_time = time.time()
        self.active_subscribers += 1
        if not self.running:
            self.start()

    def remove_subscriber(self):
        self.active_subscribers = max(0, self.active_subscribers - 1)
        if self.active_subscribers == 0:
            self.stop()

    def is_active(self) -> bool:
        return self.running and self.frame is not None
