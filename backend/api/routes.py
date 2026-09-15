"""
Core System API Routes: Health, Video Streaming, Camera Control, Screenshots, Settings.
"""
from datetime import datetime
from pathlib import Path
import time
import asyncio
import cv2
from fastapi import APIRouter, Response, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

try:
    from backend.config import SCREENSHOTS_DIR
    from backend.services.camera_service import CameraService
    from backend.services.prediction_service import PredictionService
    from backend.database.db import get_all_settings, save_setting
except ImportError:
    from config import SCREENSHOTS_DIR
    from services.camera_service import CameraService
    from services.prediction_service import PredictionService
    from database.db import get_all_settings, save_setting

router = APIRouter()


class SettingsPayload(BaseModel):
    camera_index: str = "0"
    resolution: str = "640x480"
    fps_limit: str = "30"
    detection_confidence: str = "0.50"
    max_hands: str = "2"
    theme: str = "dark"
    show_landmarks: str = "true"
    show_confidence: str = "true"


@router.get("/api/health")
def health_check():
    """System health check endpoint."""
    cam = CameraService.get_instance()
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "camera_active": cam.is_active(),
        "active_subscribers": cam.active_subscribers,
    }


async def mjpeg_frame_generator(draw_landmarks: bool = True):
    """Asynchronous low-latency generator yielding multipart JPEG frames to browser."""
    pred_service = PredictionService.get_instance()
    cam_service = CameraService.get_instance()
    cam_service.add_subscriber()

    last_sent_id = -1
    try:
        # Allow camera hardware up to 3 seconds to spin up on initial stream connection
        startup_wait = time.time()
        while not cam_service.is_active() and (time.time() - startup_wait < 3.0):
            await asyncio.sleep(0.05)

        while True:
            # Immediate break if camera was turned off or released
            if not cam_service.is_active():
                break

            # If camera hardware hasn't produced a new frame yet, yield to event loop
            if cam_service.frame_id == last_sent_id:
                await asyncio.sleep(0.003)
                continue

            ret, frame, state = pred_service.process_live_frame(draw_landmarks=draw_landmarks)
            if not ret or frame is None:
                await asyncio.sleep(0.005)
                continue

            last_sent_id = cam_service.frame_id

            # Fast lightweight JPEG encoding (quality 55 cuts bandwidth by 40% with zero visual loss)
            _, buffer = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 55, cv2.IMWRITE_JPEG_OPTIMIZE, 0]
            )
            frame_bytes = buffer.tobytes()

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

            # Yield control to event loop so telemetry requests remain ultra-responsive (<1ms)
            await asyncio.sleep(0.001)

    except (GeneratorExit, asyncio.CancelledError, Exception):
        pass
    finally:
        cam_service.remove_subscriber()
        print("[Streaming] Browser client disconnected from video feed.")


@router.get("/video_feed")
async def video_feed(landmarks: bool = True):
    """High-speed non-blocking MJPEG video streaming endpoint."""
    return StreamingResponse(
        mjpeg_frame_generator(draw_landmarks=landmarks),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/api/camera/status")
def camera_status():
    pred_service = PredictionService.get_instance()
    return pred_service.latest_state


@router.post("/api/camera/start")
@router.get("/api/camera/start")
def start_camera():
    cam = CameraService.get_instance()
    try:
        success = cam.start()
        return {"success": success, "camera_active": cam.is_active()}
    except Exception as e:
        return {"success": False, "error": str(e), "camera_active": False}


@router.post("/api/camera/stop")
@router.get("/api/camera/stop")
def stop_camera():
    """Immediately stop and release webcam hardware (supports Beacon/keepalive)."""
    cam = CameraService.get_instance()
    cam.stop()
    return {"success": True, "camera_active": False}



@router.post("/api/screenshot")
def capture_screenshot():
    """Capture and save high-resolution annotated screenshot."""
    pred_service = PredictionService.get_instance()
    ret, frame, _ = pred_service.process_live_frame()
    if not ret or frame is None:
        return JSONResponse(status_code=400, content={"success": False, "error": "Camera not ready"})

    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = SCREENSHOTS_DIR / filename
    cv2.imwrite(str(filepath), frame)

    return {
        "success": True,
        "filename": filename,
        "path": str(filepath),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/api/settings")
def fetch_settings():
    return get_all_settings()


@router.post("/api/settings")
def update_settings(payload: SettingsPayload):
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    for k, v in data.items():
        save_setting(k, str(v))
    return {"success": True, "settings": get_all_settings()}


# =====================================================================
# INTERACTIVE STUDIO MODE ENDPOINTS (HUD, Canvas, Mouse, Rehab)
# =====================================================================

class ColorPayload(BaseModel):
    color: str = "Cyan"


class BrushPayload(BaseModel):
    size: int = 5


@router.post("/api/studio/mode/{mode_id}")
def set_studio_mode(mode_id: int):
    """Switch active studio mode (1: HUD, 2: Air Canvas, 3: Virtual Mouse, 4: Rehab)."""
    pred_service = PredictionService.get_instance()
    success = pred_service.set_mode(mode_id)
    if success:
        return {"success": True, "mode": pred_service.get_mode(), "mode_name": pred_service.mode_names.get(mode_id)}
    return JSONResponse(status_code=400, content={"success": False, "error": "Invalid mode ID (1-4)"})


@router.get("/api/studio/mode")
def get_studio_mode():
    """Fetch currently active studio mode."""
    pred_service = PredictionService.get_instance()
    return {"mode": pred_service.get_mode(), "mode_name": pred_service.mode_names.get(pred_service.get_mode())}


@router.post("/api/canvas/clear")
def clear_air_canvas():
    """Clear all drawing strokes on the Air Canvas."""
    pred_service = PredictionService.get_instance()
    success = pred_service.clear_canvas()
    return {"success": success}


@router.post("/api/canvas/undo")
def undo_air_canvas():
    """Undo the last stroke on the Air Canvas."""
    pred_service = PredictionService.get_instance()
    success = pred_service.undo_canvas()
    return {"success": success}


@router.post("/api/canvas/color")
def set_canvas_color(payload: ColorPayload):
    """Select active drawing color / eraser."""
    pred_service = PredictionService.get_instance()
    success = pred_service.set_canvas_color(payload.color)
    return {"success": success, "color": payload.color}


@router.post("/api/canvas/whiteboard")
def toggle_whiteboard():
    """Toggle between camera background and clean whiteboard."""
    pred_service = PredictionService.get_instance()
    state = pred_service.toggle_whiteboard()
    return {"success": True, "whiteboard_mode": state}


@router.post("/api/canvas/brush")
def set_brush_size(payload: BrushPayload):
    """Set brush drawing thickness."""
    pred_service = PredictionService.get_instance()
    success = pred_service.set_brush_size(payload.size)
    return {"success": success, "size": payload.size}


@router.post("/api/mouse/toggle")
def toggle_virtual_mouse():
    """Enable or pause Virtual Mouse cursor control."""
    pred_service = PredictionService.get_instance()
    state = pred_service.toggle_mouse()
    return {"success": True, "mouse_enabled": state}


@router.get("/api/rehab/metrics")
def get_rehab_metrics():
    """Retrieve real-time Biometric and Rehabilitation telemetry."""
    pred_service = PredictionService.get_instance()
    return pred_service.get_rehab_metrics()
