"""
SQLite Database Manager for Gesture History, Settings, and Model Metrics.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import sqlite3
import json

try:
    from backend.config import DATABASE_PATH
except ImportError:
    from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create initial tables and performance indexes if not present."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # High-performance WAL mode for non-blocking concurrent reads & writes
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("PRAGMA cache_size = -32000;")

        # Gesture recognition history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gesture_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gesture TEXT NOT NULL,
                confidence REAL NOT NULL,
                hand_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Performance indexes for instant sorting & filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_timestamp ON gesture_history(timestamp DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_gesture ON gesture_history(gesture);")

        # Application settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # Model evaluation metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                accuracy REAL NOT NULL,
                precision REAL NOT NULL,
                recall REAL NOT NULL,
                f1_score REAL NOT NULL,
                sample_count INTEGER NOT NULL,
                trained_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed default settings if empty
        defaults = {
            "camera_index": "0",
            "resolution": "640x480",
            "fps_limit": "30",
            "detection_confidence": "0.50",
            "max_hands": "2",
            "theme": "dark",
            "show_landmarks": "true",
            "show_confidence": "true",
        }
        for k, v in defaults.items():
            cursor.execute("""
                INSERT OR IGNORE INTO app_settings (key, value)
                VALUES (?, ?)
            """, (k, v))

        conn.commit()


def log_gesture(gesture: str, confidence: float, hand_type: str = "Right") -> Optional[int]:
    """Record a recognized gesture to history."""
    if not gesture or gesture in ["No Hand", "Unknown"]:
        return None
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO gesture_history (gesture, confidence, hand_type, timestamp)
                VALUES (?, ?, ?, datetime('now', 'localtime'))
            """, (gesture, round(float(confidence), 4), hand_type))
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"[DB Error] log_gesture failed: {e}")
        return None


def get_history(limit: int = 50, offset: int = 0, query: str = "", gesture_filter: str = "") -> List[Dict[str, Any]]:
    """Retrieve historical gesture records with optional search and filter."""
    with get_connection() as conn:
        cursor = conn.cursor()
        sql = "SELECT id, gesture, confidence, hand_type, timestamp FROM gesture_history WHERE 1=1"
        params = []

        if query:
            sql += " AND (gesture LIKE ? OR hand_type LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        if gesture_filter and gesture_filter != "ALL":
            sql += " AND gesture = ?"
            params.append(gesture_filter)

        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_history_count(query: str = "", gesture_filter: str = "") -> int:
    """Get total matching rows count for pagination."""
    with get_connection() as conn:
        cursor = conn.cursor()
        sql = "SELECT COUNT(*) FROM gesture_history WHERE 1=1"
        params = []
        if query:
            sql += " AND (gesture LIKE ? OR hand_type LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        if gesture_filter and gesture_filter != "ALL":
            sql += " AND gesture = ?"
            params.append(gesture_filter)
        cursor.execute(sql, params)
        return cursor.fetchone()[0]


def clear_history() -> bool:
    """Clear all records from gesture_history."""
    with get_connection() as conn:
        conn.cursor().execute("DELETE FROM gesture_history")
        conn.commit()
        return True


def delete_history_item(item_id: int) -> bool:
    """Delete a single history record."""
    with get_connection() as conn:
        conn.cursor().execute("DELETE FROM gesture_history WHERE id = ?", (item_id,))
        conn.commit()
        return True


def get_analytics() -> Dict[str, Any]:
    """Aggregate statistics for the analytics dashboard."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Total count
        cursor.execute("SELECT COUNT(*) FROM gesture_history")
        total_detections = cursor.fetchone()[0]

        # Average confidence
        cursor.execute("SELECT AVG(confidence) FROM gesture_history")
        avg_conf_row = cursor.fetchone()[0]
        avg_confidence = round(float(avg_conf_row) * 100, 1) if avg_conf_row is not None else 0.0

        # Frequency by gesture
        cursor.execute("""
            SELECT gesture, COUNT(*) as count, AVG(confidence) as avg_conf
            FROM gesture_history
            GROUP BY gesture
            ORDER BY count DESC
            LIMIT 10
        """)
        gesture_counts = [
            {"gesture": r["gesture"], "count": r["count"], "avg_confidence": round(r["avg_conf"] * 100, 1)}
            for r in cursor.fetchall()
        ]

        # Hourly / recent distribution
        cursor.execute("""
            SELECT strftime('%H:00', timestamp) as hour, COUNT(*) as count
            FROM gesture_history
            GROUP BY hour
            ORDER BY hour DESC
            LIMIT 8
        """)
        hourly_activity = [{"hour": r["hour"], "count": r["count"]} for r in cursor.fetchall()]

        # Hand distribution
        cursor.execute("""
            SELECT hand_type, COUNT(*) as count
            FROM gesture_history
            GROUP BY hand_type
        """)
        hand_distribution = {r["hand_type"]: r["count"] for r in cursor.fetchall()}

        return {
            "total_detections": total_detections,
            "average_confidence": avg_confidence,
            "gesture_counts": gesture_counts,
            "hourly_activity": list(reversed(hourly_activity)),
            "hand_distribution": hand_distribution,
        }


def get_all_settings() -> Dict[str, str]:
    """Retrieve all current application settings."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM app_settings")
        return {r["key"]: r["value"] for r in cursor.fetchall()}


def save_setting(key: str, value: str):
    """Save or update an application setting."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, datetime('now', 'localtime'))
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        """, (key, str(value)))
        conn.commit()


def save_model_metric(model_name: str, accuracy: float, precision: float, recall: float, f1_score: float, sample_count: int):
    """Persist performance metric of a trained model."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO model_metrics (model_name, accuracy, precision, recall, f1_score, sample_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (model_name, round(accuracy, 4), round(precision, 4), round(recall, 4), round(f1_score, 4), sample_count))
        conn.commit()


def get_latest_model_metric() -> Optional[Dict[str, Any]]:
    """Retrieve the most recent model evaluation score."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT model_name, accuracy, precision, recall, f1_score, sample_count, trained_date
            FROM model_metrics
            ORDER BY id DESC LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None


# Initialize schema on module import
init_db()
