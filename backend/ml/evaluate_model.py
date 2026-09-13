"""
Evaluation and Metrics Utility for Hand Gesture Classification Models.
"""
from typing import Dict, Any, List
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix


def evaluate_classifier(model, X_test: np.ndarray, y_test: np.ndarray, target_names: List[str]) -> Dict[str, Any]:
    """
    Compute comprehensive classification metrics.
    """
    y_pred = model.predict(X_test)

    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
    recall = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
    f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

    cm = confusion_matrix(y_test, y_pred)

    # Per-class scores
    per_class_precision = precision_score(y_test, y_pred, average=None, zero_division=0)
    per_class_recall = recall_score(y_test, y_pred, average=None, zero_division=0)
    per_class_f1 = f1_score(y_test, y_pred, average=None, zero_division=0)

    class_metrics = []
    unique_labels = np.unique(np.concatenate([y_test, y_pred]))
    for idx in unique_labels:
        name = target_names[idx] if idx < len(target_names) else f"Class_{idx}"
        class_metrics.append({
            "class_name": name,
            "precision": round(float(per_class_precision[idx]), 4) if idx < len(per_class_precision) else 0.0,
            "recall": round(float(per_class_recall[idx]), 4) if idx < len(per_class_recall) else 0.0,
            "f1": round(float(per_class_f1[idx]), 4) if idx < len(per_class_f1) else 0.0,
        })

    return {
        "accuracy": round(accuracy * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1_score": round(f1 * 100, 2),
        "class_metrics": class_metrics,
        "confusion_matrix": cm.tolist(),
    }
