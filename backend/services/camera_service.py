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
                print(f"[CameraService Error] Unable to open camera on indices {indices_to_try}.")
                return False

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
        """Dedicated background loop continuously reading latest frame with frame pacing & watchdog."""
        frame_interval = 1.0 / max(10, min(60, self.fps_limit))
        while self.running:
            if self.cap is None:
                break

            # Inactivity watchdog: auto-release if no subscribers are active AND no frames read for > 15s
            if self.active_subscribers == 0 and (time.time() - self.last_access_time > 15.0):
                print("[CameraService Watchdog] Inactivity detected (>15s, 0 subscribers). Powering down camera hardware.")
                threading.Thread(target=self.stop, daemon=True).start()
                break

            # Direct hardware grab with micro-sleep pacing to prevent CPU pegging
            loop_start = time.perf_counter()
            try:
                if self.cap is not None and self.cap.grab():
                    ret, frame = self.cap.retrieve()
                    if ret and frame is not None:
                        with self.lock:
                            self.ret = ret
                            self.frame = frame
                            self.frame_id += 1
                    # Frame pace to hardware rate (~30fps) - eliminates 100% CPU busy-spin
                    elapsed = time.perf_counter() - loop_start
                    sleep_time = max(0.001, frame_interval - elapsed)
                    time.sleep(sleep_time)
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

    def add_subscriber(self):
        self.last_access_time = time.time()
        self.active_subscribers += 1
        if not self.running or self.cap is None or not self.cap.isOpened():
            self.start()

    def remove_subscriber(self):
        self.active_subscribers = max(0, self.active_subscribers - 1)
        if self.active_subscribers == 0:
            self.stop()

    def is_active(self) -> bool:
        return self.running and self.cap is not None and self.cap.isOpened()
