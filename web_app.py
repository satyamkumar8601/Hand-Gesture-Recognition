"""
Web Application & Streaming Dashboard for OmniGesture AI Studio.
High-speed, low-latency threaded camera pipeline with adaptive frame streaming.
"""
from datetime import datetime
from pathlib import Path
import asyncio
import os
import time
import cv2
import numpy as np
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
import uvicorn

from config import AppConfig, SNAPSHOT_DIR
from camera_stream import ThreadedCamera
from hand_tracker import HandTracker
from gesture_recognizer import GestureRecognizer
from air_canvas import AirCanvas
from virtual_mouse import VirtualMouse
from hud_renderer import HUDRenderer
from rehab_tracker import RehabTracker

app = FastAPI(title="OmniGesture AI Studio Web Dashboard")


class WebStudioState:
    def __init__(self):
        self.camera = None
        self.tracker = None
        self.gesture_engine = None
        self.air_canvas = None
        self.virtual_mouse = None
        self.hud = None
        self.rehab = None
        self.mode = 1  # 1: HUD, 2: Canvas, 3: Mouse, 4: Rehab
        self.is_running = False
        self.active_clients = 0
        self.latest_gesture = "None"
        self.latest_fps = 0.0

    def initialize(self):
        if self.is_running and self.camera is not None:
            return

        self.tracker = HandTracker(
            model_path=AppConfig.tracker.model_path,
            num_hands=AppConfig.tracker.num_hands,
            min_detection_confidence=AppConfig.tracker.min_hand_detection_confidence,
            min_tracking_confidence=AppConfig.tracker.min_tracking_confidence,
            smoothing_factor=AppConfig.tracker.smoothing_factor,
            inference_size=(AppConfig.tracker.inference_width, AppConfig.tracker.inference_height),
        )
        self.gesture_engine = GestureRecognizer()

        self.camera = ThreadedCamera(
            device_index=AppConfig.camera.device_index,
            width=AppConfig.camera.width,
            height=AppConfig.camera.height,
            target_fps=AppConfig.camera.target_fps,
        )

        actual_w, actual_h = AppConfig.camera.width, AppConfig.camera.height
        for _ in range(15):
            ret, frame = self.camera.read()
            if ret and frame is not None:
                actual_h, actual_w = frame.shape[:2]
                break
            time.sleep(0.05)

        self.air_canvas = AirCanvas(width=actual_w, height=actual_h)
        self.virtual_mouse = VirtualMouse(camera_w=actual_w, camera_h=actual_h)
        self.hud = HUDRenderer(width=actual_w, height=actual_h)
        self.rehab = RehabTracker(width=actual_w, height=actual_h)
        self.is_running = True

    def release_camera(self):
        if self.camera:
            self.camera.release()
            self.camera = None
        if self.tracker:
            self.tracker.close()
            self.tracker = None
        self.is_running = False
        self.latest_fps = 0.0
        self.latest_gesture = "OFF"


studio = WebStudioState()


def generate_frames():
    studio.initialize()
    studio.active_clients += 1
    prev_time = time.time()
    fps_smooth = 30.0

    try:
        while studio.is_running:
            ret, frame = studio.camera.read() if studio.camera else (False, None)
            if not ret or frame is None:
                time.sleep(0.005)
                continue

        if AppConfig.camera.flip_horizontal:
            frame = cv2.flip(frame, 1)

        now = time.time()
        dt = now - prev_time
        prev_time = now
        if dt > 0:
            fps_smooth = 0.9 * fps_smooth + 0.1 * (1.0 / dt)
        studio.latest_fps = round(fps_smooth, 1)

        hands = studio.tracker.process_frame(frame)
        gestures = [studio.gesture_engine.recognize(h) for h in hands]

        if gestures:
            studio.latest_gesture = gestures[0].name
        else:
            studio.latest_gesture = "NO HAND"

        primary_idx = 0
        for idx, h in enumerate(hands):
            if h.handedness == "Right":
                primary_idx = idx
                break

        mode_names = {1: "HUD Analytics", 2: "Air Canvas", 3: "Virtual Mouse", 4: "Biometrics & Rehab"}
        active_mode_name = mode_names.get(studio.mode, "HUD Analytics")

        if studio.mode == 2:  # Air Canvas
            if hands:
                status = studio.air_canvas.update(hands[primary_idx], gestures[primary_idx])
                if status:
                    studio.hud.notify(status, duration=1.0)
            display_frame = studio.air_canvas.render_composite(frame)
            if hands:
                accent = studio.air_canvas.current_color if not studio.air_canvas.is_eraser else (200, 200, 200)
                display_frame = studio.hud.draw_skeleton(display_frame, hands[primary_idx], accent)

        elif studio.mode == 3:  # Virtual Mouse
            display_frame = frame.copy()
            if hands:
                studio.virtual_mouse.update(hands[primary_idx], gestures[primary_idx])
                for h in hands:
                    display_frame = studio.hud.draw_skeleton(display_frame, h, AppConfig.colors.CYAN)

        elif studio.mode == 4:  # Rehab
            display_frame = frame.copy()
            for idx, h in enumerate(hands):
                accent = AppConfig.colors.CYAN if h.handedness == "Right" else AppConfig.colors.NEON_PINK
                display_frame = studio.hud.draw_skeleton(display_frame, h, accent)
            display_frame = studio.rehab.draw_rehab_dashboard(display_frame, hands, gestures)

        else:  # HUD Analytics
            display_frame = frame.copy()
            for idx, (h, g) in enumerate(zip(hands, gestures)):
                accent = AppConfig.colors.CYAN if h.handedness == "Right" else AppConfig.colors.NEON_PINK
                display_frame = studio.hud.draw_skeleton(display_frame, h, accent)
                display_frame = studio.hud.draw_bounding_box(display_frame, h, g.name)
                display_frame = studio.hud.draw_gesture_card(display_frame, h, g, slot_idx=idx)

        display_frame = studio.hud.draw_top_telemetry(display_frame, fps_smooth, active_mode_name)

        # High-speed JPEG encoding (quality 60 is crisp and flies over network without buffer latency)
        _, buffer = cv2.imencode(".jpg", display_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        frame_bytes = buffer.tobytes()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.001)
    finally:
        studio.active_clients = max(0, studio.active_clients - 1)
        if studio.active_clients == 0:
            print("[WebStudio] All browser clients disconnected. Releasing camera.")
            studio.release_camera()


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/api/camera/pause")
def pause_camera():
    studio.release_camera()
    return {"success": True, "status": "paused"}


@app.post("/api/camera/resume")
def resume_camera():
    studio.initialize()
    return {"success": True, "status": "resumed"}


@app.post("/api/camera/stop")
def stop_camera():
    studio.release_camera()
    return {"success": True, "status": "stopped"}


@app.post("/api/shutdown")
def shutdown_app():
    studio.release_camera()
    import threading
    def kill():
        time.sleep(0.6)
        os._exit(0)
    threading.Thread(target=kill, daemon=True).start()
    return {"success": True, "message": "Camera released and application stopped"}


@app.get("/api/status")
def get_status():
    return {
        "mode": studio.mode,
        "fps": studio.latest_fps,
        "gesture": studio.latest_gesture,
        "mouse_enabled": studio.virtual_mouse.enabled if studio.virtual_mouse else False,
    }


@app.post("/api/set_mode/{mode_id}")
def set_mode(mode_id: int):
    if mode_id in [1, 2, 3, 4]:
        studio.mode = mode_id
        if mode_id == 3 and studio.virtual_mouse:
            studio.virtual_mouse.enabled = True
        return {"success": True, "mode": studio.mode}
    return JSONResponse(status_code=400, content={"error": "Invalid mode id"})


@app.post("/api/canvas/clear")
def clear_canvas():
    if studio.air_canvas:
        studio.air_canvas.clear()
        studio.hud.notify("Canvas Cleared")
        return {"success": True}
    return {"success": False}


@app.post("/api/canvas/undo")
def undo_canvas():
    if studio.air_canvas:
        success = studio.air_canvas.undo()
        if success:
            studio.hud.notify("Stroke Undone")
        return {"success": success}
    return {"success": False}


@app.post("/api/snapshot")
def take_snapshot():
    if not studio.is_running:
        return {"success": False, "error": "Studio not initialized"}

    ret, frame = studio.camera.read()
    if not ret or frame is None:
        return {"success": False, "error": "Camera frame read failed"}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SNAPSHOT_DIR / f"web_snapshot_{timestamp}.png"

    if studio.mode == 2 and studio.air_canvas:
        path = studio.air_canvas.save_artwork()
    else:
        cv2.imwrite(str(path), frame)

    return {"success": True, "path": str(path), "filename": path.name}


@app.get("/", response_class=HTMLResponse)
def index():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OmniGesture AI Studio // Ultra-Low Latency Dashboard</title>
  <style>
    :root {
      --bg: #0d0f12;
      --card-bg: rgba(22, 27, 34, 0.85);
      --border: #30363d;
      --accent: #00f0ff;
      --accent-pink: #ff007f;
      --accent-green: #00ff88;
      --text: #f0f6fc;
      --text-dim: #8b949e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, sans-serif; }
    body { background: var(--bg); color: var(--text); display: flex; flex-direction: column; min-height: 100vh; }
    header {
      background: rgba(13, 15, 18, 0.95);
      border-bottom: 1px solid var(--border);
      padding: 0.8rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      backdrop-filter: blur(10px);
    }
    .brand { display: flex; align-items: center; gap: 0.75rem; font-size: 1.25rem; font-weight: 700; color: var(--accent); letter-spacing: 1px; }
    .badge-pill { background: rgba(0, 240, 255, 0.15); border: 1px solid var(--accent); color: var(--accent); padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; }
    .status-bar { display: flex; gap: 1.5rem; font-size: 0.9rem; }
    .status-item { display: flex; align-items: center; gap: 0.5rem; color: var(--text-dim); }
    .status-val { font-weight: 600; color: var(--text); }
    
    main { display: grid; grid-template-columns: 1fr 320px; gap: 1.25rem; padding: 1.25rem 2rem; flex: 1; }
    .video-card {
      background: #000;
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    }
    .video-card img { width: 100%; height: 100%; object-fit: contain; }
    
    .sidebar { display: flex; flex-direction: column; gap: 1rem; }
    .panel {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.1rem;
      backdrop-filter: blur(12px);
    }
    .panel h3 { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin-bottom: 0.8rem; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 0.4rem; }
    
    .mode-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
    .btn {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 0.7rem 0.4rem;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
      text-align: center;
    }
    .btn:hover { background: rgba(0, 240, 255, 0.15); border-color: var(--accent); color: var(--accent); }
    .btn.active { background: var(--accent); color: #000; border-color: var(--accent); box-shadow: 0 0 15px rgba(0,240,255,0.4); }
    
    .action-group { display: flex; flex-direction: column; gap: 0.5rem; }
    .btn-action { background: #21262d; border: 1px solid #363b42; }
    .btn-action:hover { background: #30363d; }
    
    .gesture-display {
      background: rgba(0,0,0,0.4);
      border-radius: 8px;
      padding: 0.8rem;
      text-align: center;
      border: 1px dashed var(--border);
    }
    .gesture-name { font-size: 1.35rem; font-weight: 800; color: var(--accent-green); margin-top: 0.2rem; letter-spacing: 1px; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span>OMNIGESTURE AI</span>
      <span class="badge-pill">ZERO-LAG TURBO</span>
    </div>
    <div class="status-bar">
      <div class="status-item">FPS: <span id="fps-val" class="status-val">--</span></div>
      <div class="status-item">Engine: <span class="status-val" style="color:var(--accent-green)">MediaPipe Vision</span></div>
    </div>
  </header>

  <main>
    <div class="video-card">
      <img src="/video_feed" alt="OmniGesture Live Stream" />
    </div>

    <div class="sidebar">
      <div class="panel">
        <h3>Interactive Modes</h3>
        <div class="mode-grid">
          <button class="btn active" id="btn-mode-1" onclick="switchMode(1)">1. Analytics</button>
          <button class="btn" id="btn-mode-2" onclick="switchMode(2)">2. Air Canvas</button>
          <button class="btn" id="btn-mode-3" onclick="switchMode(3)">3. Mouse</button>
          <button class="btn" id="btn-mode-4" onclick="switchMode(4)">4. Rehab</button>
        </div>
      </div>

      <div class="panel">
        <h3>Detected Gesture</h3>
        <div class="gesture-display">
          <div style="font-size: 0.75rem; color: var(--text-dim);">PRIMARY GESTURE</div>
          <div class="gesture-name" id="gesture-val">INITIALIZING</div>
        </div>
      </div>

      <div class="panel">
        <h3>Quick Controls</h3>
        <div class="action-group">
          <button class="btn btn-action" onclick="callApi('/api/canvas/undo')">Undo Canvas Stroke</button>
          <button class="btn btn-action" onclick="callApi('/api/canvas/clear')">Clear Canvas</button>
          <button class="btn btn-action" style="border-color: var(--accent); color: var(--accent);" onclick="takeSnapshot()">Take High-Res Snapshot</button>
          <button class="btn btn-action" style="border-color: #ff4d4f; color: #ff4d4f; margin-top: 0.5rem;" onclick="stopAndExit()">🛑 Stop Camera & Exit</button>
        </div>
      </div>
    </div>
  </main>

  <script>
    async function stopAndExit() {
      if (confirm('Are you sure you want to turn off the camera and exit?')) {
        try {
          await fetch('/api/shutdown', { method: 'POST' });
        } catch (e) {}
        document.body.innerHTML = '<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;background:#0d0f12;color:#00ff88;font-family:Segoe UI,sans-serif;text-align:center;"><h2>Webcam and server stopped successfully.</h2><p style="color:#8b949e;margin-top:12px;">The camera light is off. You can safely close this browser tab.</p></div>';
      }
    }

    async function switchMode(modeId) {
      const res = await fetch('/api/set_mode/' + modeId, { method: 'POST' });
      if (res.ok) {
        document.querySelectorAll('.mode-grid .btn').forEach((b, i) => {
          b.classList.toggle('active', (i + 1) === modeId);
        });
      }
    }

    async function callApi(url) {
      await fetch(url, { method: 'POST' });
    }

    async function takeSnapshot() {
      const res = await fetch('/api/snapshot', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        alert('Snapshot saved to: ' + data.filename);
      }
    }

    // Automatic Camera Lifecycle: Turn OFF camera when tab is not active, ON when active
    const videoImg = document.querySelector('.video-card img');

    document.addEventListener('visibilitychange', async () => {
      if (document.hidden) {
        // User switched tabs or minimized: Turn camera OFF immediately
        if (videoImg) videoImg.src = '';
        try {
          navigator.sendBeacon('/api/camera/pause');
        } catch (e) {
          fetch('/api/camera/pause', { method: 'POST', keepalive: true });
        }
        const gVal = document.getElementById('gesture-val');
        if (gVal) gVal.innerText = 'CAMERA OFF (TAB INACTIVE)';
        const fVal = document.getElementById('fps-val');
        if (fVal) fVal.innerText = '0';
      } else {
        // User returned to tab: Turn camera back ON
        try {
          await fetch('/api/camera/resume', { method: 'POST' });
        } catch (e) {}
        if (videoImg) videoImg.src = '/video_feed?' + Date.now();
      }
    });

    window.addEventListener('pagehide', () => {
      navigator.sendBeacon('/api/camera/stop');
    });

    window.addEventListener('beforeunload', () => {
      navigator.sendBeacon('/api/camera/stop');
    });

    setInterval(async () => {
      if (document.hidden) return;
      try {
        const res = await fetch('/api/status');
        if (res.ok) {
          const data = await res.json();
          document.getElementById('fps-val').innerText = data.fps;
          document.getElementById('gesture-val').innerText = data.gesture.replace('_', ' ');
        }
      } catch (e) {}
    }, 500);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    print("Starting OmniGesture Turbo Web Server on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
