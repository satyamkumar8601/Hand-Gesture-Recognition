# OmniGesture AI - Backend Service

Self-contained FastAPI real-time Machine Learning and Computer Vision backend.

---

## 🚀 Deploying to Render

You can deploy this backend to [Render](https://render.com) using either of two simple methods:

### Method 1: Render Dashboard (Recommended)

1. Sign in to [Render Dashboard](https://dashboard.render.com/) and click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the following fields:
   - **Name**: `omnigesture-backend` (or your preferred name)
   - **Region**: Any (e.g. `Oregon (US West)`)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment Variables**, add:
   - `PYTHON_VERSION` = `3.11.9`
5. Click **Create Web Service**. Render will install dependencies and start your backend!

---

### Method 2: Render Blueprint (Infrastructure as Code)

1. Connect your repository on Render.
2. Choose **New +** -> **Blueprint**.
3. Render automatically detects [`render.yaml`](../render.yaml) at repo root and provisions the web service.

---

## 🔌 API Endpoints Reference

Once deployed (e.g., at `https://omnigesture-backend.onrender.com`), the service provides:

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Service status, greeting & discovery links |
| `/docs` | `GET` | Interactive Swagger API documentation |
| `/api/health` | `GET` | Health check and camera hardware status |
| `/video_feed` | `GET` | High-speed multipart MJPEG video stream |
| `/api/gestures/list` | `GET` | Supported gestures catalog & emoji metadata |
| `/api/model/info` | `GET` | Active trained ML model metadata |
| `/api/model/train` | `POST` | Benchmark & train Random Forest / SVM / KNN |
| `/api/dataset/summary` | `GET` | Landmark samples count per gesture |
| `/api/history` | `GET` | Recent gesture classification history |
| `/api/analytics` | `GET` | Aggregate gesture distribution metrics |
| `/api/settings` | `GET/POST` | Get or update camera & vision settings |

---

## 💻 Local Development

To run the backend locally on your computer:

```bash
# Navigate to project root or backend
pip install -r backend/requirements.txt

# Run server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Or double-click `run_backend.bat` in the root folder.
