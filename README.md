<<<<<<< HEAD

https://hand-gesture-recognition-w55n.vercel.app/


# 🖐️ AI-Powered Hand Gesture Recognition System
### Real-Time Computer Vision & Machine Learning Studio using OpenCV, MediaPipe & Scikit-Learn

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF.svg)](https://vitejs.dev/)
[![MediaPipe Tasks](https://img.shields.io/badge/MediaPipe-0.10%2B-4285F4.svg)](https://developers.google.com/mediapipe)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38B2D8.svg)](https://tailwindcss.com/)

---

## 🚀 Overview

**OmniGesture AI** is an enterprise-grade Computer Vision and Machine Learning system that recognizes 17 distinct hand gestures in real time using a standard webcam. It combines Google MediaPipe Tasks 21 3D spatial landmark tracking, an 82-dimensional scale-invariant geometric feature extractor, multiple Scikit-learn classification models, an active-release camera privacy manager, and a sleek cyberpunk glassmorphism web dashboard.

---

## ✨ Key Highlights

- ⚡ **Real-Time 30+ FPS Performance**: Multi-threaded DirectShow frame capture with Exponential Moving Average (EMA) landmark smoothing.
- 🔒 **Zero-Background Camera Privacy Guarantee**: Automatically calls `cap.release()` and powers down the webcam LED the moment no client is viewing the feed.
- 🎯 **17 Hand Gestures Supported**:
  - **10 Basic Gestures**: Open Palm, Fist, Thumbs Up, Thumbs Down, Victory, One Finger, Two Fingers, Three Fingers, Four Fingers, Five Fingers.
  - **7 Advanced Gestures**: OK Sign, Rock Sign, Call Me, Point Left, Point Right, Stop, Peace.
- 🧪 **Multi-Model Machine Learning Benchmarking**: Evaluates Random Forest, Support Vector Machine (SVM), K-Nearest Neighbors (KNN), and Logistic Regression on the fly, auto-deploying the champion model (`best_model.pkl`).
- 🔄 **Hybrid Intelligent Fallback**: Automatically switches to geometric heuristic detection if model confidence drops below the threshold.
- 📊 **SQLite Persistence & Analytics**: Stores full detection history, duration, confidence, and system settings in `backend/database/gesture.db`.
- 🌐 **Modern React 18 + Vite Web Studio**: Glassmorphism UI with Tailwind CSS, Lucide icons, live audio-style probability bars, and 1-click dataset capture.

---

## 🏗️ System Architecture

```
OmniGesture AI System
│
├── 📷 Hardware Capture (OpenCV DirectShow)
│     ├── Multi-threaded frame polling (30+ FPS)
│     └── Automatic hardware release & LED shutoff when idle
│
├── 🖐️ Vision & Landmark Pipeline (Google MediaPipe Tasks)
│     ├── 21 3D spatial joint coordinates (x, y, z)
│     ├── EMA temporal smoothing (jitter reduction)
│     └── Bounding box & glowing skeleton HUD rendering
│
├── 📐 Feature Engineering (82-Dimensional Vector)
│     ├── 63 Wrist-relative normalized 3D coordinates
│     ├── 5 Fingertip-to-wrist Euclidean distances
│     ├── 5 Fingertip-to-MCP distances
│     ├── 4 Adjacent fingertip distances
│     └── 5 Binary finger curl / extension states
│
├── 🧠 Classification Engine (Scikit-Learn)
│     ├── Random Forest (100 estimators)
│     ├── Support Vector Machine (RBF kernel)
│     ├── K-Nearest Neighbors (k=5)
│     ├── Logistic Regression (L2 regularization)
│     └── Geometric rule-based fallback mode
│
├── ⚡ Backend API Gateway (FastAPI + Uvicorn)
│     ├── Multi-subscriber MJPEG `/video_feed` stream
│     ├── Real-time telemetry `/api/camera/status`
│     ├── Model training `/api/model/train` & hot-reload
│     ├── Dataset studio endpoints `/api/dataset/*`
│     └── SQLite history queries & CSV/JSON export
│
└── 💻 Frontend Studio (React 18 + Vite + Tailwind CSS)
      ├── 1. Dashboard (KPI cards, mini feed, recent activity)
      ├── 2. Live Recognition (Large HUD stream, telemetry, stats)
      ├── 3. Dataset Studio (Class browser, 1-click capture, balance view)
      ├── 4. Model Training (Algorithm benchmark, confusion matrix, retrain)
      ├── 5. Analytics (Confidence distributions, gesture frequency charts)
      ├── 6. History (Filterable table, search, CSV / JSON export)
      └── 7. Settings (Camera device, resolution, confidence sliders)
```

---

## ⚡ Quick Start & Running the Project

### Prerequisites
1. **Python 3.10+** (Tested on Python 3.11, 3.12, 3.13)
2. **Node.js 18+ & npm**
3. A standard USB or integrated webcam

---

### Option 1: 1-Click Launch (Recommended for Windows)

Simply double-click:
```bat
run.bat
```
or run from your terminal:
```bat
run_all.bat
```
This automatically starts:
- **FastAPI Backend Server** on `http://127.0.0.1:8000`
- **Vite React Frontend** on `http://localhost:5173`
- Opens your default browser to `http://localhost:5173`

---

### Option 2: Running Components Individually

#### 1. Start the Backend Server:
```bash
# Double click run_backend.bat or execute:
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at: `http://127.0.0.1:8000/docs`

#### 2. Start the Frontend Studio:
```bash
# Double click run_frontend.bat or execute:
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

#### 3. Run Native OpenCV Desktop Window:
```bash
python main.py
```

---

## 🌐 Deploy to GitHub & Vercel Guide

### 1. Push Code to GitHub

The repository is already configured with clean `.gitignore` and `.gitattributes`.

```bash
# 1. Initialize git (if not already done)
git init

# 2. Stage all project files
git add .

# 3. Create initial commit
git commit -m "feat: Production-ready OmniGesture AI Studio with Vercel & GitHub deployment"

# 4. Set default branch to main
git branch -M main

# 5. Link to your GitHub repository (replace with your repo URL)
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPOSITORY_NAME>.git

# 6. Push to GitHub
git push -u origin main
```

---

### 2. Deploy Frontend to Vercel

The frontend is ready for **1-click zero-config deployment on Vercel**:

#### Method A: Via Vercel Web Dashboard (Recommended)
1. Go to [vercel.com/new](https://vercel.com/new) and log in.
2. Select and import your GitHub repository: `omnigesture-ai`.
3. Vercel will automatically detect the configuration from `vercel.json`:
   - **Framework Preset**: `Vite`
   - **Build Command**: `cd frontend && npm install && npm run build` (or `npm run build`)
   - **Output Directory**: `frontend/dist`
4. *(Optional)* Under **Environment Variables**, add:
   - `VITE_API_URL`: Your deployed cloud backend URL (e.g., `https://omnigesture-backend.onrender.com`).
   *(You can also leave this blank and configure it directly in the live app's Settings page!)*
5. Click **Deploy**. Your app will be live globally in seconds with a free `.vercel.app` URL!

#### Method B: Via Vercel CLI
```bash
# In the project root:
npx vercel
# Follow the interactive prompts, or for production:
npx vercel --prod
```

---

### 3. Deploy Backend (Render / Railway / Fly.io)

Because camera inference uses OpenCV and MediaPipe, the Python backend runs on a continuous web service:

#### Deploy to Render (Free Tier):
1. Log in to [render.com](https://render.com) and click **New +** &rarr; **Blueprint**.
2. Connect your GitHub repository.
3. Render will read `render.yaml` automatically and configure:
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Click **Apply**. Once deployed, copy your service URL (e.g. `https://omnigesture-backend.onrender.com`).

#### Connect Frontend & Backend:
1. Open your deployed Vercel site.
2. Navigate to **Settings &rarr; Cloud & Backend API Connectivity**.
3. Paste your Render backend URL and click **Apply** & **Test Ping**!
4. The Navbar badge will turn **🟢 Online** and all live camera, training, and database features will be fully functional!

## 📁 Repository Directory Structure

```
ML project/
├── backend/
│   ├── api/
│   │   ├── routes.py                # Camera, streaming, health, and settings routes
│   │   └── gesture_routes.py        # Training, dataset collection, history & analytics
│   ├── database/
│   │   ├── db.py                    # SQLite database interface (gesture.db)
│   │   └── gesture.db               # SQLite database file
│   ├── ml/
│   │   ├── feature_extractor.py     # 82-dim scale-invariant feature extraction
│   │   ├── train_model.py           # Multi-model benchmarking & training script
│   │   ├── evaluate_model.py        # Metrics: Accuracy, Precision, Recall, F1
│   │   ├── model_loader.py          # Hot-reloading model inference manager
│   │   ├── best_model.pkl           # Trained champion classifier
│   │   └── label_encoder.pkl        # Label encoder mapping
│   ├── services/
│   │   ├── camera_service.py        # Threaded DirectShow capture & auto-off manager
│   │   ├── hand_detector.py         # MediaPipe Tasks HandLandmarker wrapper
│   │   ├── gesture_detector.py      # ML + Geometric rule hybrid detector
│   │   └── prediction_service.py    # Real-time frame analysis & HUD renderer
│   ├── config.py                    # Server configuration & gesture definitions
│   ├── main.py                      # FastAPI application entry point
│   └── requirements.txt             # Python backend dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/              # Sidebar, Navbar, CameraFeed, GestureCard, Notification
│   │   ├── context/AppContext.jsx   # Global state, camera telemetry, settings
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx        # KPI metrics & quick overview
│   │   │   ├── LiveRecognition.jsx  # Fullscreen camera HUD & probability bars
│   │   │   ├── Dataset.jsx          # Live dataset collection studio
│   │   │   ├── TrainModel.jsx       # Multi-model benchmark & retraining UI
│   │   │   ├── Analytics.jsx        # Confidence distributions & charts
│   │   │   ├── History.jsx          # Searchable log & CSV/JSON export
│   │   │   └── Settings.jsx         # Hardware, vision & model tuning
│   │   ├── App.jsx                  # Main layout & router
│   │   ├── main.jsx                 # React root mount
│   │   └── index.css                # Cyberpunk glassmorphism design system
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── dataset/
│   └── gestures.csv                 # 17-class feature dataset (1,020 samples)
├── scripts/
│   ├── collect_data.py              # CLI dataset collection tool
│   └── test_camera.py               # Hardware camera diagnostic script
├── run.bat                          # Main interactive launcher
├── run_all.bat                      # 1-Click full stack launcher
├── run_backend.bat                  # Backend server launcher
├── run_frontend.bat                 # Frontend server launcher
└── README.md                        # Documentation
```

---

## 🎯 Supported Gestures (17 Total)

| No. | Gesture Name | Emoji | Detection Mode | Description |
|:---:|:---|:---:|:---:|:---|
| 1 | `Open Palm` | ✋ | ML + Heuristic | All 5 fingers fully extended |
| 2 | `Fist` | ✊ | ML + Heuristic | All 5 fingers tightly curled into palm |
| 3 | `Thumbs Up` | 👍 | ML + Heuristic | Thumb pointing upwards, all other fingers closed |
| 4 | `Thumbs Down` | 👎 | ML + Heuristic | Thumb pointing downwards, all other fingers closed |
| 5 | `Victory` | ✌️ | ML + Heuristic | Index and middle fingers extended in V-shape |
| 6 | `One Finger` | ☝️ | ML + Heuristic | Index finger pointing up only |
| 7 | `Two Fingers` | ✌️ | ML + Heuristic | Index and middle fingers together |
| 8 | `Three Fingers` | 🤟 | ML + Heuristic | Thumb, index, and middle extended |
| 9 | `Four Fingers` | 🖖 | ML + Heuristic | Four fingers extended, thumb curled |
| 10 | `Five Fingers` | 🖐️ | ML + Heuristic | Full five fingers splayed |
| 11 | `OK Sign` | 👌 | ML + Heuristic | Thumb and index tips touching, others extended |
| 12 | `Rock Sign` | 🤘 | ML + Heuristic | Index and pinky extended, middle and ring curled |
| 13 | `Call Me` | 🤙 | ML + Heuristic | Thumb and pinky extended, middle 3 curled |
| 14 | `Point Left` | 👈 | ML + Heuristic | Index finger pointing horizontally left |
| 15 | `Point Right`| 👉 | ML + Heuristic | Index finger pointing horizontally right |
| 16 | `Stop` | 🛑 | ML + Heuristic | Open palm facing forward at close range |
| 17 | `Peace` | ☮️ | ML + Heuristic | Splayed index and middle fingers |

---

## 🔒 Zero-Background Camera Privacy Guarantee

Many computer vision applications keep the webcam hardware running continuously in the background, keeping the physical camera LED turned on and draining battery/privacy.

In **OmniGesture AI**:
1. When no browser tab is viewing the video feed, the backend subscriber count drops to `0`.
2. The `CameraService` triggers an automatic teardown: calling `cap.release()` and shutting down the worker thread.
3. The **physical webcam LED turns completely OFF**.
4. When you open or return to the Live Recognition feed, the camera starts up seamlessly in ~200ms.

---

## 🧪 Training & Machine Learning Pipeline

1. **Feature Extraction**:
   - Each frame with a detected hand produces an 82-dimensional vector.
   - Coordinates are normalized relative to the wrist `(x0, y0, z0)` and scaled by palm span `||MCP_middle - wrist||`, making the model completely invariant to user distance from the camera.
2. **Model Benchmark**:
   - The `/api/model/train` endpoint trains 4 distinct classifiers on `dataset/gestures.csv` with 5-fold stratified cross validation.
   - Outputs: Accuracy, Precision, Recall, F1-Score, and a complete Confusion Matrix.
   - The highest performing model is serialized to `backend/ml/best_model.pkl` and hot-reloaded into the running inference service with zero downtime.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|:---:|:---|
| <kbd>1</kbd> - <kbd>7</kbd> | Navigate across the 7 pages instantly |
| <kbd>Space</kbd> | Start / Pause video stream |
| <kbd>S</kbd> | Capture timestamped PNG screenshot |
| <kbd>C</kbd> | Quick-collect current gesture sample into dataset |
| <kbd>F</kbd> | Toggle Fullscreen camera view |

---

## 🚀 Cloud Deployment: Vercel + Render

### 1. Render (FastAPI Backend)
- **Repository**: Connect your GitHub repository.
- **Root Directory**: Leave **empty / blank** (do NOT enter `ML_PROJECT`).
- **Environment**: `Python`
- **Build Command**: `pip install -r backend/requirements.txt`
- **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `PYTHON_VERSION`: `3.11.9`

### 2. Vercel (React Frontend)
- **Repository**: Connect your GitHub repository.
- **Framework Preset**: `Vite`
- **Root Directory**: `.` (or `frontend`)
- **Environment Variables**:
  - `VITE_API_URL`: Your Render service URL (e.g., `https://hand-gesture-recognition.onrender.com`)
- **In-App Dynamic Switching**:
  - Navigate to the **Settings** page in the web app.
  - Paste your Render backend URL into the **FastAPI Backend Connection** card and click **Apply** to test and persist the connection live!

---

## 🛡️ License

MIT License &copy; 2026 OmniGesture AI Contributors. Built for computer vision, machine learning, and HCI research.
