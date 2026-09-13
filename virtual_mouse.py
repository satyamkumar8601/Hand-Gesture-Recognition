"""
Virtual Mouse Controller module.
Maps hand movements and gestures to mouse cursor positioning, clicks, dragging, and scrolling.
"""
from typing import Optional, Tuple
import time
import numpy as np

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.001
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False

from config import AppConfig
from hand_tracker import HandData, INDEX_TIP, THUMB_TIP, MIDDLE_TIP
from gesture_recognizer import GestureResult


class VirtualMouse:
    """Controls OS mouse pointer and clicks via hand landmarks."""

    def __init__(self, camera_w: int = 1280, camera_h: int = 720):
        self.camera_w = camera_w
        self.camera_h = camera_h
        self.enabled = False

        if PYAUTOGUI_AVAILABLE:
            try:
                self.screen_w, self.screen_h = pyautogui.size()
            except Exception:
                self.screen_w, self.screen_h = (1920, 1080)
        else:
            self.screen_w, self.screen_h = (1920, 1080)

        # Active boundary box inside camera frame to reach full screen easily
        margin_x = int(camera_w * AppConfig.mouse.edge_margin_x)
        margin_y = int(camera_h * AppConfig.mouse.edge_margin_y)
        self.box_x1 = margin_x
        self.box_x2 = camera_w - margin_x
        self.box_y1 = margin_y
        self.box_y2 = camera_h - margin_y

        # Smoothing state
        self.smooth_x = self.screen_w / 2.0
        self.smooth_y = self.screen_h / 2.0
        self.prev_time = time.time()

        # Click & drag state
        self.is_dragging = False
        self.last_click_time = 0.0
        self.pinch_start_time = 0.0

        # Scroll state
        self.prev_scroll_y: Optional[float] = None

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        if not self.enabled and self.is_dragging and PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.mouseUp()
            except Exception:
                pass
            self.is_dragging = False
        return self.enabled

    def update(self, hand: HandData, gesture: GestureResult) -> Optional[str]:
        """
        Process hand data and trigger mouse events.
        """
        if not self.enabled or not PYAUTOGUI_AVAILABLE:
            return None

        status_msg: Optional[str] = None
        lm = hand.landmarks_pixel
        finger_states = gesture.finger_states

        # Index fingertip position
        raw_x, raw_y = lm[INDEX_TIP]

        # 1. Map camera coordinates (clamped to inner box) to full screen resolution
        clamped_x = np.clip(raw_x, self.box_x1, self.box_x2)
        clamped_y = np.clip(raw_y, self.box_y1, self.box_y2)

        norm_x = (clamped_x - self.box_x1) / (self.box_x2 - self.box_x1)
        norm_y = (clamped_y - self.box_y1) / (self.box_y2 - self.box_y1)

        target_screen_x = norm_x * self.screen_w
        target_screen_y = norm_y * self.screen_h

        # Exponential smoothing
        alpha = AppConfig.mouse.smoothing
        self.smooth_x = alpha * target_screen_x + (1.0 - alpha) * self.smooth_x
        self.smooth_y = alpha * target_screen_y + (1.0 - alpha) * self.smooth_y

        # Handle Dynamic Gestures for Slides / Media
        if gesture.dynamic_gesture == "SWIPE_LEFT":
            try:
                pyautogui.press("right")
                return "Slide Next ->"
            except Exception:
                pass
        elif gesture.dynamic_gesture == "SWIPE_RIGHT":
            try:
                pyautogui.press("left")
                return "<- Slide Prev"
            except Exception:
                pass

        # 2. SCROLL MODE: Index and Middle fingers both extended
        if finger_states.index and finger_states.middle and not finger_states.ring and not finger_states.pinky:
            current_y = (lm[INDEX_TIP][1] + lm[MIDDLE_TIP][1]) / 2.0
            if self.prev_scroll_y is not None:
                dy = current_y - self.prev_scroll_y
                if abs(dy) > 10:
                    scroll_amount = -int(dy * 1.5)
                    try:
                        pyautogui.scroll(scroll_amount)
                        status_msg = f"Scrolling ({'Up' if scroll_amount > 0 else 'Down'})"
                    except Exception:
                        pass
            self.prev_scroll_y = current_y
            return status_msg
        else:
            self.prev_scroll_y = None

        # Move mouse cursor when pointing or pinching
        if finger_states.index:
            try:
                pyautogui.moveTo(int(self.smooth_x), int(self.smooth_y))
            except Exception:
                pass

        # 3. CLICK & DRAG via Pinch (Thumb + Index)
        now = time.time()
        if gesture.is_pinch:
            if self.pinch_start_time == 0.0:
                self.pinch_start_time = now

            pinch_duration = now - self.pinch_start_time

            # If held longer than 0.35s -> Drag mode
            if pinch_duration > 0.35 and not self.is_dragging:
                try:
                    pyautogui.mouseDown()
                    self.is_dragging = True
                    status_msg = "Mouse Dragging"
                except Exception:
                    pass
        else:
            if self.pinch_start_time > 0.0:
                pinch_duration = now - self.pinch_start_time
                self.pinch_start_time = 0.0

                if self.is_dragging:
                    try:
                        pyautogui.mouseUp()
                        self.is_dragging = False
                        status_msg = "Drop / Released Drag"
                    except Exception:
                        pass
                elif pinch_duration < 0.35:
                    # Quick tap -> Click
                    if (now - self.last_click_time) < AppConfig.mouse.double_click_interval:
                        try:
                            pyautogui.doubleClick()
                            status_msg = "Double Click"
                        except Exception:
                            pass
                    else:
                        try:
                            pyautogui.click()
                            status_msg = "Left Click"
                        except Exception:
                            pass
                    self.last_click_time = now

        # 4. RIGHT CLICK via OK sign
        if gesture.name == "OK_SIGN" and (now - self.last_click_time) > 0.6:
            try:
                pyautogui.rightClick()
                self.last_click_time = now
                status_msg = "Right Click"
            except Exception:
                pass

        return status_msg
