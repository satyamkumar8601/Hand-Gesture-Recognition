"""
High-performance threaded camera stream with zero-latency buffer flushing.
"""
from typing import Optional, Tuple
import threading
import time
import cv2
import numpy as np


class ThreadedCamera:
    """
    Dedicated thread for video capture to eliminate OpenCV buffer lag
    and ensure the application always receives the freshest available frame.
    """

    def __init__(self, device_index: int = 0, width: int = 640, height: int = 480, target_fps: int = 30):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.target_fps = target_fps

        # Attempt DirectShow first on Windows for lowest latency
        self.cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(device_index)

        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video capture device {device_index}")

        # Set low buffer size to prevent queuing
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, target_fps)

        # Warm up
        self.ret, self.frame = self.cap.read()
        if not self.ret or self.frame is None:
            # Retry once
            time.sleep(0.2)
            self.ret, self.frame = self.cap.read()

        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.thread.start()

    def _capture_worker(self):
        frame_interval = 1.0 / max(10, min(60, self.target_fps))
        while self.running:
            if self.cap is None:
                break
            loop_start = time.perf_counter()
            if self.cap.grab():
                ret, frame = self.cap.retrieve()
                if ret and frame is not None:
                    with self.lock:
                        self.ret = ret
                        self.frame = frame
                elapsed = time.perf_counter() - loop_start
                sleep_time = max(0.001, frame_interval - elapsed)
                time.sleep(sleep_time)
            else:
                time.sleep(0.004)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Return the freshest frame with zero latency."""
        with self.lock:
            if not self.running or not self.ret or self.frame is None:
                return False, None
            return True, self.frame.copy()

    def pause(self):
        """Release the camera hardware and stop worker (turns camera light OFF)."""
        self.running = False
        if hasattr(self, "thread") and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if hasattr(self, "cap") and self.cap is not None:
            try:
                if self.cap.isOpened():
                    self.cap.release()
            except Exception:
                pass
            self.cap = None

    def resume(self) -> bool:
        """Re-open the webcam hardware and restart capture (turns camera light ON)."""
        if self.running and self.cap is not None and self.cap.isOpened():
            return True

        self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.device_index)

        if not self.cap.isOpened():
            return False

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self.ret, self.frame = self.cap.read()
        self.running = True
        self.thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.thread.start()
        return True

    @property
    def is_paused(self) -> bool:
        return not self.running or self.cap is None

    def release(self):
        self.pause()
