"""
Main Application Entrypoint for AI-Powered Hand Gesture Recognition API.
"""
from contextlib import asynccontextmanager
from pathlib import Path
import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

try:
    from backend.config import BEST_MODEL_PATH
except ImportError:
    from config import BEST_MODEL_PATH
from database.db import init_db
from api.routes import router as core_router
from api.gesture_routes import router as gesture_router
from services.camera_service import CameraService
from ml.model_loader import ModelLoader


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: initialize resources on startup, release on shutdown."""
    print("==========================================================")
    print("  [INIT] AI-POWERED HAND GESTURE RECOGNITION BACKEND STARTING ")
    print("==========================================================")
    init_db()

    # Load Best Model if present
    loader = ModelLoader.get_instance()
    if loader.is_loaded:
        print(f"[Startup] Active Model: {loader.package.get('model_name', 'Trained Classifier')}")
    else:
        print("[Startup] No trained ML model found. Initializing with Demo Mode (Rule-Based Heuristics).")

    yield

    # Shutdown: ensure webcam hardware is released immediately
    print("\n[Shutdown] Releasing camera hardware and background services...")
    CameraService.get_instance().stop()
    print("[Shutdown] Clean exit complete.")


app = FastAPI(
    title="AI-Powered Hand Gesture Recognition API",
    description="Full-stack real-time Computer Vision & Machine Learning gesture classification service.",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS for React + Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(core_router)
app.include_router(gesture_router)


@app.get("/")
def root():
    """Root health and service discovery endpoint for Render and API clients."""
    return {
        "service": "AI-Powered Hand Gesture Recognition API",
        "status": "online",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "video_feed": "/video_feed",
    }


@app.get("/api/debug")
def debug_status():
    """Diagnostic endpoint to pinpoint exact startup or runtime exceptions."""
    import traceback
    info = {"status": "ok"}
    try:
        from services.prediction_service import PredictionService
        ps = PredictionService.get_instance()
        info["prediction_service"] = "initialized"
        info["mode"] = ps.get_mode()
        info["telemetry"] = ps.latest_state
    except Exception as e:
        info["prediction_service_error"] = f"{type(e).__name__}: {e}"
        info["prediction_service_traceback"] = traceback.format_exc()

    try:
        from services.camera_service import CameraService
        cam = CameraService.get_instance()
        info["camera_running"] = cam.running
        info["camera_active"] = cam.is_active()
    except Exception as e:
        info["camera_error"] = str(e)

    return info


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Starting FastAPI Backend on http://{host}:{port} ...")
    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
