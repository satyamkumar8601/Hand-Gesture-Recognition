"""
Gesture Recognition, Machine Learning, Dataset Collection, and Analytics API Routes.
"""
from typing import Optional, List, Dict, Any
import csv
import io
import pandas as pd
from fastapi import APIRouter, Response, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    from backend.config import DATASET_FILE, ALL_GESTURES, GESTURE_ICONS, GESTURES_BASIC, GESTURES_ADVANCED
    from backend.ml.model_loader import ModelLoader
    from backend.ml.train_model import train_and_compare_models
    from backend.ml.feature_extractor import FeatureExtractor
    from backend.services.camera_service import CameraService
    from backend.services.hand_detector import HandDetector
    from backend.database.db import (
        get_history,
        get_history_count,
        clear_history,
        delete_history_item,
        get_analytics,
        get_latest_model_metric,
        log_gesture,
    )
except ImportError:
    from config import DATASET_FILE, ALL_GESTURES, GESTURE_ICONS, GESTURES_BASIC, GESTURES_ADVANCED
    from ml.model_loader import ModelLoader
    from ml.train_model import train_and_compare_models
    from ml.feature_extractor import FeatureExtractor
    from services.camera_service import CameraService
    from services.hand_detector import HandDetector
    from database.db import (
        get_history,
        get_history_count,
        clear_history,
        delete_history_item,
        get_analytics,
        get_latest_model_metric,
        log_gesture,
    )

router = APIRouter()


class CollectSamplePayload(BaseModel):
    gesture_name: str
    count: int = 1
    image_base64: Optional[str] = None


@router.get("/api/gestures/list")
def list_gestures():
    """Returns complete catalog of supported gestures with metadata."""
    return {
        "all_gestures": ALL_GESTURES,
        "basic_gestures": GESTURES_BASIC,
        "advanced_gestures": GESTURES_ADVANCED,
        "icons": GESTURE_ICONS,
        "total_count": len(ALL_GESTURES),
    }


@router.get("/api/model/info")
def model_information():
    """Retrieve details about the currently active machine learning model."""
    loader = ModelLoader.get_instance()
    info = loader.get_info()
    metric_record = get_latest_model_metric()
    if metric_record:
        info["latest_metrics"] = metric_record

    try:
        from services.prediction_service import PredictionService
        ps = PredictionService.get_instance()
        detector = getattr(ps, "hand_detector", None)
        info["detector_status"] = {
            "detector_initialized": detector is not None,
            "image_landmarker_loaded": getattr(detector, "image_landmarker", None) is not None if detector else False,
            "video_landmarker_loaded": getattr(detector, "landmarker", None) is not None if detector else False,
            "model_path": getattr(detector, "model_path", ""),
            "last_error": getattr(detector, "_last_error", None) if detector else None,
        }
    except Exception as det_err:
        info["detector_status"] = {"error": str(det_err)}

    return info


@router.post("/api/model/reload")
def reload_model_endpoint():
    """Hot reload active machine learning model from disk."""
    try:
        loader = ModelLoader.get_instance()
        loader.reload()
        info = loader.get_info()
        return {"success": True, "message": "Model reloaded successfully", "model_info": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/model/train")
def train_model_endpoint():
    """
    Triggers multi-model training pipeline:
    Trains Random Forest, SVM, KNN, Logistic Regression, compares metrics,
    selects best model, updates SQLite, and hot-reloads model in memory.
    """
    try:
        report = train_and_compare_models()
        # Hot-reload in ModelLoader instance
        loader = ModelLoader.get_instance()
        loader.reload()
        return {
            "success": True,
            "message": f"Successfully trained models! Best: {report['best_model']} ({report['best_accuracy']}%)",
            "report": report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/dataset/summary")
def dataset_summary():
    """Return sample counts per gesture and dataset health."""
    if not DATASET_FILE.exists():
        # Auto-create directory and empty representation
        counts = {g: 0 for g in ALL_GESTURES}
        return {"total_samples": 0, "samples_per_class": counts, "classes_count": len(ALL_GESTURES)}

    try:
        df = pd.read_csv(DATASET_FILE)
        counts = {g: 0 for g in ALL_GESTURES}
        if "label" in df.columns:
            real_counts = df["label"].value_counts().to_dict()
            for k, v in real_counts.items():
                counts[k] = int(v)
        return {
            "total_samples": len(df),
            "samples_per_class": counts,
            "classes_count": len(ALL_GESTURES),
        }
    except Exception as e:
        counts = {g: 0 for g in ALL_GESTURES}
        return {"total_samples": 0, "samples_per_class": counts, "error": str(e)}


from services.prediction_service import PredictionService


class CollectBatchPayload(BaseModel):
    gesture_name: str
    count: int = 10
    image_base64: Optional[str] = None


@router.post("/api/dataset/collect")
def collect_sample(payload: CollectSamplePayload):
    """
    Capture hand landmarks from live webcam or browser base64 frame and append to dataset.
    """
    gesture_name = payload.gesture_name
    if gesture_name not in ALL_GESTURES:
        raise HTTPException(status_code=400, detail=f"Invalid gesture name. Must be one of: {ALL_GESTURES}")

    pred_service = PredictionService.get_instance()
    detector = pred_service.hand_detector

    frame = None
    if payload.image_base64:
        import base64
        import numpy as np
        import cv2
        try:
            data = payload.image_base64
            if "," in data:
                data = data.split(",", 1)[1]
            img_bytes = base64.b64decode(data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if decoded is not None:
                frame = cv2.flip(decoded, 1)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image_base64: {e}")

    if frame is None:
        cam = CameraService.get_instance()
        if not cam.is_active():
            cam.start()
            time.sleep(0.15)
        ret, frame = cam.read_frame()
        if not ret or frame is None:
            raise HTTPException(status_code=400, detail="Webcam frame not available. Please ensure camera is running.")

    hands = detector.process_image(frame) if hasattr(detector, "process_image") else detector.process_frame(frame)
    if not hands:
        return {"success": False, "message": "No hand detected in camera frame. Please show hand clearly to camera."}

    primary = hands[0]
    features = FeatureExtractor.extract_features(primary.landmarks_pixel, primary.landmarks_world, primary.handedness)
    feature_names = FeatureExtractor.get_feature_names()

    # Append to CSV
    row_dict = {name: float(val) for name, val in zip(feature_names, features)}
    row_dict["label"] = gesture_name

    file_exists = DATASET_FILE.exists()
    df_new = pd.DataFrame([row_dict])
    df_new.to_csv(DATASET_FILE, mode="a", header=not file_exists, index=False)

    return {
        "success": True,
        "gesture": gesture_name,
        "handedness": primary.handedness,
        "message": f"Collected 1 sample for '{gesture_name}'.",
    }


@router.post("/api/dataset/collect_batch")
def collect_batch(payload: CollectBatchPayload):
    """
    Burst collect multiple samples across frames or augmented variants from browser frame.
    """
    gesture_name = payload.gesture_name
    if gesture_name not in ALL_GESTURES:
        raise HTTPException(status_code=400, detail=f"Invalid gesture name. Must be one of: {ALL_GESTURES}")

    pred_service = PredictionService.get_instance()
    detector = pred_service.hand_detector
    feature_names = FeatureExtractor.get_feature_names()
    target_count = max(1, min(25, payload.count))

    collected_rows = []

    if payload.image_base64:
        import base64
        import numpy as np
        import cv2
        try:
            data = payload.image_base64
            if "," in data:
                data = data.split(",", 1)[1]
            img_bytes = base64.b64decode(data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if decoded is not None:
                frame = cv2.flip(decoded, 1)
                hands = detector.process_image(frame) if hasattr(detector, "process_image") else detector.process_frame(frame)
                if hands:
                    primary = hands[0]
                    for i in range(target_count):
                        # i=0 uses exact landmarks; subsequent use micro-jitter for robust data distribution
                        if i == 0:
                            lm_px = primary.landmarks_pixel
                            lm_world = primary.landmarks_world
                        else:
                            lm_px = primary.landmarks_pixel + np.random.normal(0, 0.8, primary.landmarks_pixel.shape)
                            lm_world = primary.landmarks_world + np.random.normal(0, 0.001, primary.landmarks_world.shape)
                        features = FeatureExtractor.extract_features(lm_px, lm_world, primary.handedness)
                        row_dict = {name: float(val) for name, val in zip(feature_names, features)}
                        row_dict["label"] = gesture_name
                        collected_rows.append(row_dict)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image_base64: {e}")
    else:
        cam = CameraService.get_instance()
        if not cam.is_active():
            cam.start()
            time.sleep(0.15)

        for _ in range(target_count * 2):
            if len(collected_rows) >= target_count:
                break
            ret, frame = cam.read_frame()
            if ret and frame is not None:
                hands = detector.process_frame(frame)
                if hands:
                    primary = hands[0]
                    features = FeatureExtractor.extract_features(primary.landmarks_pixel, primary.landmarks_world, primary.handedness)
                    row_dict = {name: float(val) for name, val in zip(feature_names, features)}
                    row_dict["label"] = gesture_name
                    collected_rows.append(row_dict)
            time.sleep(0.04)

    if not collected_rows:
        return {"success": False, "message": "No hand detected during burst. Please hold hand steady in front of camera."}

    file_exists = DATASET_FILE.exists()
    df_new = pd.DataFrame(collected_rows)
    df_new.to_csv(DATASET_FILE, mode="a", header=not file_exists, index=False)

    return {
        "success": True,
        "gesture": gesture_name,
        "count": len(collected_rows),
        "message": f"Successfully collected {len(collected_rows)} burst samples for '{gesture_name}'!",
    }


@router.delete("/api/dataset/{gesture_name}")
def delete_class_samples(gesture_name: str):
    """Delete all dataset samples belonging to a specific gesture."""
    if not DATASET_FILE.exists():
        return {"success": True, "deleted_count": 0}

    df = pd.read_csv(DATASET_FILE)
    if "label" in df.columns:
        orig_len = len(df)
        df = df[df["label"] != gesture_name]
        deleted_count = orig_len - len(df)
        df.to_csv(DATASET_FILE, index=False)
        return {"success": True, "deleted_count": deleted_count}
    return {"success": True, "deleted_count": 0}


@router.get("/api/history")
def get_gesture_history(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    query: str = Query("", max_length=50),
    gesture_filter: str = Query("", max_length=50),
):
    """Retrieve filtered recognition history with pagination."""
    items = get_history(limit=limit, offset=offset, query=query, gesture_filter=gesture_filter)
    total = get_history_count(query=query, gesture_filter=gesture_filter)

    # Attach icons
    for it in items:
        it["icon"] = GESTURE_ICONS.get(it["gesture"], "✨")

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/api/history/{item_id}")
def delete_single_history(item_id: int):
    success = delete_history_item(item_id)
    return {"success": success}


@router.delete("/api/history")
def clear_all_history():
    success = clear_history()
    return {"success": success, "message": "All history logs cleared."}


@router.get("/api/history/export")
def export_history(format: str = Query("csv", pattern="^(csv|json)$")):
    """Export all gesture logs to CSV or JSON format."""
    items = get_history(limit=5000, offset=0)
    if format == "json":
        return JSONResponse(content=items)

    # Generate CSV response
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "gesture", "confidence", "hand_type", "timestamp"])
    writer.writeheader()
    for row in items:
        writer.writerow({
            "id": row["id"],
            "gesture": row["gesture"],
            "confidence": f"{round(row['confidence'] * 100, 1)}%",
            "hand_type": row["hand_type"],
            "timestamp": row["timestamp"],
        })

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=gesture_history.csv"
    return response


@router.get("/api/analytics")
def get_analytics_data():
    """Retrieve consolidated analytics metrics for charts."""
    return get_analytics()


class PredictFramePayload(BaseModel):
    image_base64: str


@router.post("/api/predict/frame")
def predict_frame(payload: PredictFramePayload):
    """
    Real-time browser webcam frame inference endpoint.
    Accepts base64-encoded frame from browser webcam, runs 3D MediaPipe Hand Landmarker,
    classifies gesture via ML / heuristics, and returns full telemetry to browser.
    """
    import base64
    import numpy as np
    import cv2
    try:
        data = payload.image_base64
        if "," in data:
            data = data.split(",", 1)[1]
        img_bytes = base64.b64decode(data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return JSONResponse(status_code=400, content={"error": "Invalid image data"})

        # Flip horizontally to match mirror interaction and training coordinates
        frame = cv2.flip(frame, 1)

        from services.prediction_service import PredictionService
        ps = PredictionService.get_instance()
        if ps.hand_detector is None:
            return {
                "hand_detected": False,
                "hands_count": 0,
                "primary_gesture": "No Hand",
                "confidence": 0.0,
                "is_ml": False,
                "icon": "✋",
                "finger_states": {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False},
                "probabilities": {},
            }

        detector = ps.hand_detector
        hands = detector.process_image(frame) if hasattr(detector, "process_image") else detector.process_frame(frame)
        if not hands:
            ps.last_logged_gesture = None
            if hasattr(ps, 'latest_state') and isinstance(ps.latest_state, dict):
                ps.latest_state.update({
                    "camera_active": True,
                    "hand_detected": False,
                    "hands_count": 0,
                    "primary_gesture": "No Hand",
                    "confidence": 0.0,
                    "is_ml": False,
                    "icon": "❌",
                    "finger_states": {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False},
                    "probabilities": {},
                    "rehab_grip_closure": 0.0,
                    "rehab_extended_fingers": 0,
                })
            return {
                "hand_detected": False,
                "hands_count": 0,
                "primary_gesture": "No Hand",
                "confidence": 0.0,
                "is_ml": False,
                "icon": "❌",
                "finger_states": {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False},
                "probabilities": {},
                "rehab_grip_closure": 0.0,
                "rehab_extended_fingers": 0,
            }

        res = ps.gesture_detector.recognize(hands[0])
        landmarks = []
        if hasattr(hands[0], 'raw_normalized') and hands[0].raw_normalized is not None:
            landmarks = [[round(float(p[0]), 4), round(float(p[1]), 4)] for p in hands[0].raw_normalized]

        # Calculate Biometric / Rehab metrics (grip closure % and extended finger count)
        grip_closure_val = 0.0
        try:
            lm = np.array(hands[0].raw_normalized)
            wrist = lm[0, :2]
            hand_size = max(hands[0].hand_scale, 1e-4)
            tip_indices = [4, 8, 12, 16, 20]
            distances = [np.linalg.norm(lm[i, :2] - wrist) for i in tip_indices]
            avg_dist = float(np.mean(distances)) / hand_size
            norm_grip = 1.0 - np.clip((avg_dist - 0.6) / (1.7 - 0.6), 0.0, 1.0)
            grip_closure_val = round(float(norm_grip * 100.0), 1)
        except Exception:
            pass

        total_extended = res.finger_states.count_extended()

        # Debounced database logging for cloud / browser webcam
        if res.name not in ["No Hand", "Unknown"]:
            import time
            now = time.time()
            if res.name != ps.last_logged_gesture or (now - ps.last_log_time > 2.5):
                try:
                    log_gesture(res.name, res.confidence, res.handedness)
                except Exception as log_err:
                    print(f"[Gesture Log Error] {log_err}")
                ps.last_logged_gesture = res.name
                ps.last_log_time = now

        telemetry = {
            "hand_detected": True,
            "hands_count": len(hands),
            "primary_gesture": res.name,
            "confidence": round(res.confidence * 100, 1),
            "is_ml": res.is_ml,
            "icon": res.icon,
            "finger_states": res.finger_states.as_dict(),
            "probabilities": res.probabilities,
            "handedness": res.handedness,
            "landmarks": landmarks,
            "rehab_grip_closure": grip_closure_val,
            "rehab_extended_fingers": total_extended,
        }

        # Keep server state in sync so telemetry status poller stays aligned
        if hasattr(ps, 'latest_state') and isinstance(ps.latest_state, dict):
            ps.latest_state.update({
                "camera_active": True,
                "hand_detected": True,
                "hands_count": len(hands),
                "primary_gesture": res.name,
                "confidence": telemetry["confidence"],
                "is_ml": res.is_ml,
                "icon": res.icon,
                "finger_states": telemetry["finger_states"],
                "probabilities": res.probabilities,
                "rehab_grip_closure": grip_closure_val,
                "rehab_extended_fingers": total_extended,
            })

        return telemetry
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
