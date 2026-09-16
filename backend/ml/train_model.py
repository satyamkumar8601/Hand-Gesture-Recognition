"""
Multi-Model Machine Learning Training & Comparison Suite for Gesture Recognition.
Trains and benchmarks Random Forest, SVM, KNN, and Logistic Regression.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
import os
import sys

# Ensure backend root is on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

try:
    from backend.config import DATASET_DIR, DATASET_FILE, BEST_MODEL_PATH, MODELS_DIR, ALL_GESTURES
except ImportError:
    from config import DATASET_DIR, DATASET_FILE, BEST_MODEL_PATH, MODELS_DIR, ALL_GESTURES
try:
    from backend.ml.feature_extractor import FeatureExtractor
    from backend.ml.evaluate_model import evaluate_classifier
    from backend.database.db import save_model_metric
except ImportError:
    from ml.feature_extractor import FeatureExtractor
    from ml.evaluate_model import evaluate_classifier
    from database.db import save_model_metric


def generate_seed_dataset_if_missing(min_samples_per_class: int = 60) -> pd.DataFrame:
    """
    Generate mathematically structured seed samples for all 17 gestures
    if no dataset exists, ensuring the ML pipeline is fully functional from day one.
    """
    if DATASET_FILE.exists():
        try:
            df = pd.read_csv(DATASET_FILE)
            if len(df) >= len(ALL_GESTURES) * 10:
                return df
        except Exception:
            pass

    print("[ML] Generating rich geometric seed dataset for 17 gestures...")
    feature_names = FeatureExtractor.get_feature_names()
    rows = []

    np.random.seed(42)

    # Anatomical finger configuration [Thumb, Index, Middle, Ring, Pinky]
    # 1.0 = extended, 0.0 = curled
    gesture_specs = {
        "Open Palm":    {"f": [1.0, 1.0, 1.0, 1.0, 1.0], "dir": "up", "pinch": False},
        "Five Fingers": {"f": [1.0, 1.0, 1.0, 1.0, 1.0], "dir": "up", "pinch": False},
        "Stop":         {"f": [1.0, 1.0, 1.0, 1.0, 1.0], "dir": "up", "pinch": False},
        "Fist":         {"f": [0.0, 0.0, 0.0, 0.0, 0.0], "dir": "fist", "pinch": False},
        "Thumbs Up":    {"f": [1.0, 0.0, 0.0, 0.0, 0.0], "dir": "thumb_up", "pinch": False},
        "Thumbs Down":  {"f": [1.0, 0.0, 0.0, 0.0, 0.0], "dir": "thumb_down", "pinch": False},
        "One Finger":   {"f": [0.0, 1.0, 0.0, 0.0, 0.0], "dir": "up", "pinch": False},
        "Two Fingers":  {"f": [0.0, 1.0, 1.0, 0.0, 0.0], "dir": "up", "pinch": False},
        "Victory":      {"f": [0.0, 1.0, 1.0, 0.0, 0.0], "dir": "v_shape", "pinch": False},
        "Peace":        {"f": [0.0, 1.0, 1.0, 0.0, 0.0], "dir": "v_shape", "pinch": False},
        "Three Fingers":{"f": [0.0, 1.0, 1.0, 1.0, 0.0], "dir": "up", "pinch": False},
        "Four Fingers": {"f": [0.0, 1.0, 1.0, 1.0, 1.0], "dir": "up", "pinch": False},
        "OK Sign":      {"f": [0.2, 0.2, 1.0, 1.0, 1.0], "dir": "ok", "pinch": True},
        "Rock Sign":    {"f": [0.0, 1.0, 0.0, 0.0, 1.0], "dir": "up", "pinch": False},
        "Call Me":      {"f": [1.0, 0.0, 0.0, 0.0, 1.0], "dir": "shaka", "pinch": False},
        "Point Left":   {"f": [0.0, 1.0, 0.0, 0.0, 0.0], "dir": "left", "pinch": False},
        "Point Right":  {"f": [0.0, 1.0, 0.0, 0.0, 0.0], "dir": "right", "pinch": False},
    }

    finger_mcp_bases = [
        (-0.25, -0.25),  # Thumb
        (-0.15, -0.50),  # Index
        (0.00,  -0.55),  # Middle
        (0.15,  -0.50),  # Ring
        (0.28,  -0.45),  # Pinky
    ]

    for gesture, spec in gesture_specs.items():
        profile = spec["f"]
        direction = spec["dir"]
        is_pinch = spec["pinch"]

        for _ in range(min_samples_per_class):
            landmarks_21 = np.zeros((21, 3), dtype=np.float32)
            # Wrist at 0
            landmarks_21[0] = [0.0, 0.0, 0.0]

            # Build 5 finger chains
            chain_indices = [
                [1, 2, 3, 4],       # Thumb
                [5, 6, 7, 8],       # Index
                [9, 10, 11, 12],    # Middle
                [13, 14, 15, 16],   # Ring
                [17, 18, 19, 20],   # Pinky
            ]

            for f_idx, chain in enumerate(chain_indices):
                bx, by = finger_mcp_bases[f_idx]
                is_ext = profile[f_idx] > 0.5

                if f_idx == 0:  # Thumb
                    if direction == "thumb_up":
                        tx, ty = bx - 0.15, -0.70
                    elif direction == "thumb_down":
                        tx, ty = bx - 0.15, 0.35
                    elif is_pinch:
                        tx, ty = -0.06, -0.45
                    elif direction == "shaka":
                        tx, ty = -0.45, -0.25
                    else:
                        tx, ty = (bx - 0.20, by - 0.35) if is_ext else (bx + 0.05, by + 0.05)
                else:  # Index, Middle, Ring, Pinky
                    if f_idx == 1 and is_pinch:
                        tx, ty = -0.06, -0.45
                    elif f_idx == 1 and direction == "left":
                        tx, ty = -0.75, by
                    elif f_idx == 1 and direction == "right":
                        tx, ty = 0.75, by
                    elif direction == "v_shape" and f_idx == 1:
                        tx, ty = bx - 0.12, -0.90
                    elif direction == "v_shape" and f_idx == 2:
                        tx, ty = bx + 0.12, -0.90
                    else:
                        tx = bx + np.random.normal(0, 0.02)
                        ty = (by - 0.45) if is_ext else (by + 0.10)

                # Interpolate 4 joints in chain
                for step, lm_idx in enumerate(chain):
                    alpha = (step + 1) / 4.0
                    jx = bx + alpha * (tx - bx) + np.random.normal(0, 0.015)
                    jy = by + alpha * (ty - by) + np.random.normal(0, 0.015)
                    jz = np.random.normal(0, 0.02)
                    landmarks_21[lm_idx] = [jx, jy, jz]

            # Compute features using the exact standard pipeline
            scale = 1.0
            wrist = landmarks_21[0][:2]
            pts = landmarks_21[:, :2]

            feat = []
            # 1. 21 3D normalized relative to wrist (63)
            for i in range(21):
                diff = landmarks_21[i] - landmarks_21[0]
                feat.extend([float(diff[0]), float(diff[1]), float(diff[2])])

            # 2. Tip to wrist distances (5)
            tips = [4, 8, 12, 16, 20]
            for tip in tips:
                feat.append(float(np.linalg.norm(pts[tip] - wrist)))

            # 3. Tip to MCP distances (5)
            mcps = [2, 5, 9, 13, 17]
            for tip, mcp in zip(tips, mcps):
                feat.append(float(np.linalg.norm(pts[tip] - pts[mcp])))

            # 4. Adjacent tip distances (4)
            feat.append(float(np.linalg.norm(pts[4] - pts[8])))
            feat.append(float(np.linalg.norm(pts[8] - pts[12])))
            feat.append(float(np.linalg.norm(pts[12] - pts[16])))
            feat.append(float(np.linalg.norm(pts[16] - pts[20])))

            # 5. Extension states (5)
            for f_idx in range(5):
                feat.append(float(profile[f_idx]))

            row_dict = {name: val for name, val in zip(feature_names, feat)}
            row_dict["label"] = gesture
            rows.append(row_dict)

    df = pd.DataFrame(rows)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATASET_FILE, index=False)
    print(f"[ML] Saved seed dataset with {len(df)} samples across {len(gesture_specs)} classes to {DATASET_FILE}")
    return df


def train_and_compare_models(test_size: float = 0.20) -> Dict[str, Any]:
    """
    Train and benchmark Random Forest, SVM, KNN, and Logistic Regression.
    Saves the best-performing model to best_model.pkl.
    """
    df = generate_seed_dataset_if_missing()

    if len(df) < 20:
        raise ValueError("Insufficient dataset samples to train models.")

    feature_cols = [c for c in df.columns if c != "label"]
    X = df[feature_cols].values
    y_raw = df["label"].values

    # Encode labels
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)
    class_names = list(label_encoder.classes_)

    # Stratified Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    # Feature Scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Model Definitions (Optimized for both high accuracy and fast non-blocking cloud benchmarking)
    candidate_models = {
        "Random Forest": RandomForestClassifier(n_estimators=60, max_depth=12, random_state=42, n_jobs=1),
        "Support Vector Machine": SVC(kernel="rbf", C=3.0, probability=True, max_iter=300, random_state=42),
        "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=5, weights="distance"),
        "Logistic Regression": LogisticRegression(max_iter=500, C=2.0, random_state=42),
    }

    comparison_results: List[Dict[str, Any]] = []
    best_model_name = None
    best_score = -1.0
    best_model_obj = None

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("  TRAINING & BENCHMARKING MACHINE LEARNING GESTURE MODELS")
    print("=" * 60)

    for name, model in candidate_models.items():
        print(f"[*] Training {name} on {len(X_train)} samples...")
        start_t = datetime.now()
        model.fit(X_train_scaled, y_train)
        duration_s = (datetime.now() - start_t).total_seconds()

        # Evaluate
        metrics = evaluate_classifier(model, X_test_scaled, y_test, class_names)
        f1 = metrics["f1_score"]
        acc = metrics["accuracy"]

        print(f"    -> Accuracy: {acc}% | F1-Score: {f1}% (took {duration_s:.2f}s)")

        # Save individual candidate model
        model_file = MODELS_DIR / f"{name.lower().replace(' ', '_')}.pkl"
        joblib.dump({"model": model, "scaler": scaler, "encoder": label_encoder}, model_file)

        # Log metric to SQLite database
        save_model_metric(
            model_name=name,
            accuracy=acc,
            precision=metrics["precision"],
            recall=metrics["recall"],
            f1_score=f1,
            sample_count=len(df),
        )

        comparison_results.append({
            "model_name": name,
            "accuracy": acc,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1_score": f1,
            "training_time_s": round(duration_s, 2),
            "is_best": False,
        })

        if f1 > best_score:
            best_score = f1
            best_model_name = name
            best_model_obj = model

    # Mark the best model
    for item in comparison_results:
        if item["model_name"] == best_model_name:
            item["is_best"] = True

    # Persist Best Model Package
    best_package = {
        "model_name": best_model_name,
        "model": best_model_obj,
        "scaler": scaler,
        "label_encoder": label_encoder,
        "class_names": class_names,
        "feature_names": feature_cols,
        "accuracy": best_score,
        "trained_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_samples": len(df),
    }
    joblib.dump(best_package, BEST_MODEL_PATH)
    print("=" * 60)
    print(f"[OK] Best Model Selected: {best_model_name} (F1: {best_score}%)")
    print(f"[OK] Saved to: {BEST_MODEL_PATH}")
    print("=" * 60 + "\n")

    return {
        "best_model": best_model_name,
        "best_accuracy": best_score,
        "total_samples": len(df),
        "total_classes": len(class_names),
        "classes": class_names,
        "trained_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "comparison": comparison_results,
    }


if __name__ == "__main__":
    train_and_compare_models()
