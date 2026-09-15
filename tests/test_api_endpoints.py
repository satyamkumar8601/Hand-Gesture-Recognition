"""
Integration tests for FastAPI Backend API endpoints.
Verifies all routes, studio controls, dataset summary, history, analytics, and CORS.
"""
from pathlib import Path
import sys
import unittest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from fastapi.testclient import TestClient
from backend.main import app


class TestBackendAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("service", data)
        self.assertIn("health", data)

    def test_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "running")
        self.assertIn("timestamp", data)
        self.assertIn("camera_active", data)

    def test_cors_vercel_headers(self):
        """Verify Vercel frontend requests receive valid CORS response headers."""
        vercel_origin = "https://omnigesture-frontend.vercel.app"
        res = self.client.get("/api/health", headers={"Origin": vercel_origin})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), vercel_origin)

    def test_gestures_catalog(self):
        res = self.client.get("/api/gestures/list")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("all_gestures", data)
        self.assertGreaterEqual(len(data["all_gestures"]), 10)
        self.assertIn("Open Palm", data["all_gestures"])
        self.assertIn("icons", data)

    def test_model_info(self):
        res = self.client.get("/api/model/info")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("model_name", data)

    def test_settings_read_and_write(self):
        # Fetch current settings
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 200)
        original_settings = res.json()
        self.assertIsInstance(original_settings, dict)

        # Update settings
        payload = {
            "camera_index": "0",
            "resolution": "640x480",
            "fps_limit": "30",
            "detection_confidence": "0.60",
            "max_hands": "2",
            "theme": "dark",
            "show_landmarks": "true",
            "show_confidence": "true",
        }
        update_res = self.client.post("/api/settings", json=payload)
        self.assertEqual(update_res.status_code, 200)
        updated_data = update_res.json()
        self.assertTrue(updated_data.get("success"))
        self.assertEqual(updated_data["settings"].get("detection_confidence"), "0.60")

    def test_studio_modes(self):
        # Test mode 1 (HUD)
        res = self.client.post("/api/studio/mode/1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["mode"], 1)

        # Test mode 2 (Canvas)
        res = self.client.post("/api/studio/mode/2")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["mode"], 2)

        # Test mode 3 (Virtual Mouse)
        res = self.client.post("/api/studio/mode/3")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["mode"], 3)

        # Test mode 4 (Rehab)
        res = self.client.post("/api/studio/mode/4")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["mode"], 4)

        # Query mode
        get_res = self.client.get("/api/studio/mode")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["mode"], 4)

        # Reset back to Mode 1 (HUD)
        self.client.post("/api/studio/mode/1")

    def test_air_canvas_controls(self):
        # Set brush color
        res = self.client.post("/api/canvas/color", json={"color": "Neon Pink"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Set brush size
        res = self.client.post("/api/canvas/brush", json={"size": 10})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Whiteboard toggle
        res = self.client.post("/api/canvas/whiteboard")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Clear canvas
        res = self.client.post("/api/canvas/clear")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

    def test_virtual_mouse_toggle(self):
        res = self.client.post("/api/mouse/toggle")
        self.assertEqual(res.status_code, 200)
        self.assertIn("mouse_enabled", res.json())

    def test_rehab_metrics(self):
        res = self.client.get("/api/rehab/metrics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, dict)

    def test_dataset_summary(self):
        res = self.client.get("/api/dataset/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_samples", data)
        self.assertIn("samples_per_class", data)

    def test_history_and_analytics(self):
        # History
        res = self.client.get("/api/history?limit=10&offset=0")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("items", data)
        self.assertIn("total", data)

        # Analytics
        res_analytics = self.client.get("/api/analytics")
        self.assertEqual(res_analytics.status_code, 200)
        data_analytics = res_analytics.json()
        self.assertIsInstance(data_analytics, dict)


if __name__ == "__main__":
    unittest.main()
