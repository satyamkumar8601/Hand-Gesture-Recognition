import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Camera, CameraOff, Sparkles, Eye, EyeOff, Loader2, RefreshCw, Video, Cloud, Download } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiUrl, getVideoFeedUrl } from '../config/api';

const PALETTE_MAP = {
  Cyan: '#06b6d4',
  Magenta: '#ec4899',
  Yellow: '#eab308',
  Emerald: '#10b981',
  Violet: '#8b5cf6',
  White: '#ffffff',
  Eraser: 'eraser',
};

const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],        // Thumb
  [0, 5], [5, 6], [6, 7], [7, 8],        // Index
  [5, 9], [9, 10], [10, 11], [11, 12],   // Middle
  [9, 13], [13, 14], [14, 15], [15, 16], // Ring
  [13, 17], [17, 18], [18, 19], [19, 20],// Pinky
  [0, 17],                               // Palm Base
];

// Calculate exact pixel rectangle of video content inside object-contain letterboxing
const getVideoRenderRect = (video) => {
  if (!video) return { x: 0, y: 0, width: 640, height: 480 };
  const vW = video.videoWidth || 640;
  const vH = video.videoHeight || 480;
  const cW = video.clientWidth || 640;
  const cH = video.clientHeight || 480;
  if (!vW || !vH || !cW || !cH) return { x: 0, y: 0, width: cW, height: cH };

  const videoRatio = vW / vH;
  const containerRatio = cW / cH;
  let renderW, renderH, x, y;

  if (containerRatio > videoRatio) {
    renderH = cH;
    renderW = cH * videoRatio;
    x = (cW - renderW) / 2;
    y = 0;
  } else {
    renderW = cW;
    renderH = cW / videoRatio;
    x = 0;
    y = (cH - renderH) / 2;
  }
  return { x, y, width: renderW, height: renderH };
};

export const CameraFeed = () => {
  const {
    liveState,
    setLiveState,
    startCamera,
    stopCamera,
    addNotification,
    voiceEnabled,
    speakGesture,
  } = useApp();

  const [showLandmarks, setShowLandmarks] = useState(true);
  const [capturing, setCapturing] = useState(false);
  const [feedKey, setFeedKey] = useState(() => Date.now());
  const [streamError, setStreamError] = useState(false);

  // Default to Browser Webcam on cloud hosts (e.g. Vercel); Backend Stream on localhost
  const isCloudHost = typeof window !== 'undefined' &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1';

  const [streamMode, setStreamMode] = useState(isCloudHost ? 'browser' : 'backend');
  const [browserCamReady, setBrowserCamReady] = useState(false);
  const [camPermissionError, setCamPermissionError] = useState(false);

  const videoRef = useRef(null);
  const grabCanvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const isPredictingRef = useRef(false);

  // Air Canvas strokes & landmarks cache
  const strokesRef = useRef([]);
  const currentStrokeRef = useRef(null);
  const landmarksRef = useRef([]);

  const videoUrl = getVideoFeedUrl(showLandmarks, feedKey);

  // Redraw overlay (strokes + MediaPipe skeleton landmarks + reticle)
  const renderOverlay = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // If Whiteboard mode is enabled, paint solid slate background
    if (liveState.whiteboard_mode) {
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    // 1. Draw saved Air Canvas strokes
    const allStrokes = [...strokesRef.current];
    if (currentStrokeRef.current && currentStrokeRef.current.points.length > 0) {
      allStrokes.push(currentStrokeRef.current);
    }

    allStrokes.forEach(stroke => {
      if (!stroke.points || stroke.points.length < 2) return;
      ctx.save();
      if (stroke.color === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
        ctx.strokeStyle = 'rgba(0,0,0,1)';
      } else {
        ctx.strokeStyle = stroke.color || '#06b6d4';
        ctx.shadowBlur = 6;
        ctx.shadowColor = stroke.color || '#06b6d4';
      }
      ctx.lineWidth = stroke.size || 8;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      ctx.beginPath();
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      if (stroke.points.length === 2) {
        ctx.lineTo(stroke.points[1].x, stroke.points[1].y);
      } else {
        for (let i = 1; i < stroke.points.length - 1; i++) {
          const xc = (stroke.points[i].x + stroke.points[i + 1].x) / 2;
          const yc = (stroke.points[i].y + stroke.points[i + 1].y) / 2;
          ctx.quadraticCurveTo(stroke.points[i].x, stroke.points[i].y, xc, yc);
        }
        const last = stroke.points[stroke.points.length - 1];
        ctx.lineTo(last.x, last.y);
      }
      ctx.stroke();
      ctx.restore();
    });

    // 2. Draw Hand Skeleton Landmarks if enabled
    const landmarks = landmarksRef.current;
    if (showLandmarks && landmarks && landmarks.length >= 21) {
      const rect = videoRef.current ? getVideoRenderRect(videoRef.current) : { x: 0, y: 0, width: canvas.width, height: canvas.height };

      // Video is mirrored (-scale-x-100), backend flips the frame, so x matches screen directly
      const pts = landmarks.map(pt => ({
        x: rect.x + pt[0] * rect.width,
        y: rect.y + pt[1] * rect.height,
      }));

      // Draw bones
      ctx.save();
      ctx.strokeStyle = '#00f2fe';
      ctx.lineWidth = 2.5;
      ctx.shadowBlur = 8;
      ctx.shadowColor = '#00f2fe';
      HAND_CONNECTIONS.forEach(([start, end]) => {
        if (pts[start] && pts[end]) {
          ctx.beginPath();
          ctx.moveTo(pts[start].x, pts[start].y);
          ctx.lineTo(pts[end].x, pts[end].y);
          ctx.stroke();
        }
      });

      // Draw joint dots
      pts.forEach((p, idx) => {
        ctx.beginPath();
        const isTip = [4, 8, 12, 16, 20].includes(idx);
        ctx.arc(p.x, p.y, isTip ? 4.5 : 3, 0, Math.PI * 2);
        ctx.fillStyle = isTip ? '#38bdf8' : '#ffffff';
        ctx.shadowBlur = isTip ? 10 : 4;
        ctx.shadowColor = '#38bdf8';
        ctx.fill();
      });

      // If Air Canvas mode: Draw cursor reticle on index finger tip (index 8)
      if (liveState.mode === 2 && pts[8]) {
        const activeHex = PALETTE_MAP[liveState.canvas_color] || '#06b6d4';
        ctx.beginPath();
        ctx.arc(pts[8].x, pts[8].y, 10, 0, Math.PI * 2);
        ctx.strokeStyle = activeHex === 'eraser' ? '#f43f5e' : activeHex;
        ctx.lineWidth = 2.5;
        ctx.shadowBlur = 12;
        ctx.shadowColor = activeHex === 'eraser' ? '#f43f5e' : activeHex;
        ctx.stroke();
      }
      ctx.restore();
    }
  }, [liveState.whiteboard_mode, liveState.mode, liveState.canvas_color, showLandmarks]);

  // Listen to canvas clear / undo events
  useEffect(() => {
    const handleClear = () => {
      strokesRef.current = [];
      currentStrokeRef.current = null;
      renderOverlay();
    };
    const handleUndo = () => {
      strokesRef.current.pop();
      renderOverlay();
    };

    window.addEventListener('omni_clear_canvas', handleClear);
    window.addEventListener('omni_undo_canvas', handleUndo);
    return () => {
      window.removeEventListener('omni_clear_canvas', handleClear);
      window.removeEventListener('omni_undo_canvas', handleUndo);
    };
  }, [renderOverlay]);

  // 1. Browser Webcam Lifecycle
  const startBrowserWebcam = useCallback(async () => {
    setCamPermissionError(false);

    // Reuse existing stream if already active
    if (mediaStreamRef.current && mediaStreamRef.current.active) {
      if (videoRef.current && videoRef.current.srcObject !== mediaStreamRef.current) {
        videoRef.current.srcObject = mediaStreamRef.current;
        videoRef.current.play().catch(() => {});
      }
      setBrowserCamReady(true);
      setLiveState(prev => ({ ...prev, camera_active: true, is_browser_cam: true }));
      return;
    }

    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: 'user',
          },
          audio: false,
        });

        mediaStreamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
        setBrowserCamReady(true);
        setLiveState(prev => ({ ...prev, camera_active: true, is_browser_cam: true }));
      } else {
        setCamPermissionError(true);
        addNotification('Webcam API is not supported in this browser', 'error');
      }
    } catch (err) {
      console.warn('Webcam permission error:', err);
      setCamPermissionError(true);
      setBrowserCamReady(false);
      addNotification('Camera access denied. Please click the camera icon in your URL bar to allow permissions.', 'error');
    }
  }, [addNotification, setLiveState]);

  const stopBrowserWebcam = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    landmarksRef.current = [];
    currentStrokeRef.current = null;
    setBrowserCamReady(false);
    setLiveState(prev => ({ ...prev, camera_active: false, is_browser_cam: false }));
    renderOverlay();
  }, [renderOverlay, setLiveState]);

  // Ensure video element receives stream whenever browserCamReady changes
  useEffect(() => {
    if (browserCamReady && videoRef.current && mediaStreamRef.current) {
      if (videoRef.current.srcObject !== mediaStreamRef.current) {
        videoRef.current.srcObject = mediaStreamRef.current;
      }
      videoRef.current.play().catch(() => {});
    }
  }, [browserCamReady]);

  // Manage camera mode switches cleanly
  useEffect(() => {
    if (streamMode === 'browser') {
      stopCamera(true);
      startBrowserWebcam();
      return () => {
        stopBrowserWebcam();
      };
    } else {
      stopBrowserWebcam();
      startCamera(true);
      return () => {
        stopCamera(true);
      };
    }
  }, [streamMode]);

  // Sync overlay canvas size to video bounding box
  const syncCanvasDimensions = useCallback(() => {
    if (!videoRef.current || !overlayCanvasRef.current) return;
    const video = videoRef.current;
    const canvas = overlayCanvasRef.current;
    if (video.clientWidth > 0 && video.clientHeight > 0) {
      if (canvas.width !== video.clientWidth || canvas.height !== video.clientHeight) {
        canvas.width = video.clientWidth;
        canvas.height = video.clientHeight;
        renderOverlay();
      }
    }
  }, [renderOverlay]);

  useEffect(() => {
    window.addEventListener('resize', syncCanvasDimensions);
    return () => window.removeEventListener('resize', syncCanvasDimensions);
  }, [syncCanvasDimensions]);

  // 2. Throttled Non-Blocking AI Inference Loop for Browser Webcam
  useEffect(() => {
    if (streamMode !== 'browser' || !browserCamReady) return;

    let timerId = null;
    let isActive = true;

    const runInference = async () => {
      if (!isActive) return;

      if (
        !isPredictingRef.current &&
        videoRef.current &&
        videoRef.current.readyState >= 2 &&
        videoRef.current.videoWidth > 0 &&
        grabCanvasRef.current
      ) {
        const video = videoRef.current;
        syncCanvasDimensions();

        const grabCanvas = grabCanvasRef.current;
        const grabCtx = grabCanvas.getContext('2d');
        const vW = video.videoWidth || 640;
        const vH = video.videoHeight || 480;
        const targetW = 320;
        const targetH = Math.max(160, Math.round((targetW * vH) / vW));
        grabCanvas.width = targetW;
        grabCanvas.height = targetH;
        grabCtx.drawImage(video, 0, 0, targetW, targetH);

        const b64 = grabCanvas.toDataURL('image/jpeg', 0.5);
        isPredictingRef.current = true;

        try {
          const res = await fetch(apiUrl('/api/predict/frame'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: b64 }),
          });

          if (res.ok && isActive) {
            const data = await res.json();
            if (data && data.hand_detected) {
              setLiveState(prev => ({
                ...prev,
                hand_detected: true,
                hands_count: data.hands_count || 1,
                primary_gesture: data.primary_gesture || 'Unknown',
                confidence: data.confidence || 0,
                is_ml: !!data.is_ml,
                icon: data.icon || '✋',
                finger_states: data.finger_states || prev.finger_states,
                probabilities: data.probabilities || prev.probabilities,
                camera_active: true,
                is_browser_cam: true,
                rehab_grip_closure: data.rehab_grip_closure !== undefined ? data.rehab_grip_closure : prev.rehab_grip_closure,
                rehab_extended_fingers: data.rehab_extended_fingers !== undefined ? data.rehab_extended_fingers : prev.rehab_extended_fingers,
              }));

              // Cache landmarks for skeleton overlay
              if (data.landmarks && Array.isArray(data.landmarks)) {
                landmarksRef.current = data.landmarks;

                // Mode 2: Air Canvas Drawing with Index Finger
                if (liveState.mode === 2 && data.landmarks.length > 8 && overlayCanvasRef.current) {
                  const idxTip = data.landmarks[8];
                  const rect = getVideoRenderRect(video);
                  const screenPt = {
                    x: rect.x + idxTip[0] * rect.width,
                    y: rect.y + idxTip[1] * rect.height,
                  };

                  const isDrawingGesture =
                    data.primary_gesture === 'Index Pointing' ||
                    data.primary_gesture === 'Point' ||
                    data.primary_gesture === 'One Finger' ||
                    (data.finger_states && data.finger_states.index && !data.finger_states.middle);

                  const isHoverGesture =
                    data.primary_gesture === 'Peace' ||
                    data.primary_gesture === 'Victory' ||
                    (data.finger_states && data.finger_states.index && data.finger_states.middle);

                  if (isDrawingGesture) {
                    const colorHex = PALETTE_MAP[liveState.canvas_color] || '#06b6d4';
                    if (!currentStrokeRef.current) {
                      currentStrokeRef.current = {
                        color: colorHex,
                        size: 6,
                        points: [screenPt],
                      };
                    } else {
                      currentStrokeRef.current.points.push(screenPt);
                    }
                  } else if (isHoverGesture) {
                    // Hover mode: finalize current stroke
                    if (currentStrokeRef.current && currentStrokeRef.current.points.length > 0) {
                      strokesRef.current.push(currentStrokeRef.current);
                      currentStrokeRef.current = null;
                    }
                  }
                }
              }

              renderOverlay();

              if (voiceEnabled && data.primary_gesture) {
                speakGesture(data.primary_gesture);
              }
            } else if (isActive) {
              landmarksRef.current = [];
              if (currentStrokeRef.current && currentStrokeRef.current.points.length > 0) {
                strokesRef.current.push(currentStrokeRef.current);
                currentStrokeRef.current = null;
              }
              renderOverlay();

              setLiveState(prev => ({
                ...prev,
                hand_detected: false,
                hands_count: 0,
                primary_gesture: 'No Hand',
                confidence: 0,
                camera_active: true,
                is_browser_cam: true,
                rehab_grip_closure: 0,
                rehab_extended_fingers: 0,
              }));
            }
          }
        } catch (e) {
          // Silent catch to keep stream fluid
        } finally {
          isPredictingRef.current = false;
        }
      }

      if (isActive) {
        // Fast adaptive pause: 80ms on localhost for silky 12 FPS response, 200ms on cloud
        const pause = isCloudHost ? 200 : 80;
        timerId = setTimeout(runInference, pause);
      }
    };

    timerId = setTimeout(runInference, 400);

    return () => {
      isActive = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [streamMode, browserCamReady, setLiveState, voiceEnabled, speakGesture, liveState.mode, liveState.canvas_color, renderOverlay, syncCanvasDimensions]);

  // Screenshot Snapshot Action
  const handleScreenshot = async () => {
    if (capturing) return;
    setCapturing(true);

    if (streamMode === 'browser' && videoRef.current) {
      try {
        const video = videoRef.current;
        const snapCanvas = document.createElement('canvas');
        const w = video.videoWidth || 640;
        const h = video.videoHeight || 480;
        snapCanvas.width = w;
        snapCanvas.height = h;
        const sctx = snapCanvas.getContext('2d');

        // Mirror video to match UI
        sctx.save();
        sctx.translate(w, 0);
        sctx.scale(-1, 1);
        sctx.drawImage(video, 0, 0, w, h);
        sctx.restore();

        // Overlay Air Canvas drawings if present
        if (overlayCanvasRef.current) {
          sctx.drawImage(overlayCanvasRef.current, 0, 0, w, h);
        }

        const link = document.createElement('a');
        link.download = `omnigesture_snapshot_${Date.now()}.png`;
        link.href = snapCanvas.toDataURL('image/png');
        link.click();
        addNotification('Screenshot downloaded', 'success');
      } catch (err) {
        addNotification('Snapshot capture failed', 'error');
      } finally {
        setCapturing(false);
      }
      return;
    }

    try {
      const res = await fetch(apiUrl('/api/screenshot'), { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        addNotification(`Captured: ${data.filename}`, 'success');
      } else {
        addNotification(data.error || 'Capture failed', 'error');
      }
    } catch (e) {
      addNotification('Screenshot error. Is backend connected?', 'error');
    } finally {
      setCapturing(false);
    }
  };

  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-light-border dark:border-dark-border flex flex-col w-full shadow-lg">
      <canvas ref={grabCanvasRef} className="hidden" />

      {/* Top Controls Header Bar */}
      <div className="px-3 sm:px-5 py-3 border-b border-light-border dark:border-dark-border flex flex-wrap items-center justify-between gap-2.5 bg-slate-50/50 dark:bg-slate-900/40">
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${
              (streamMode === 'browser' ? browserCamReady : liveState.camera_active)
                ? liveState.hand_detected
                  ? 'bg-accent shadow-glow-accent animate-pulse'
                  : 'bg-emerald-400'
                : 'bg-rose-500'
            }`}
          />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
            {(streamMode === 'browser' ? browserCamReady : liveState.camera_active)
              ? liveState.hand_detected
                ? `🟢 Hand Active (${liveState.hands_count || 1})`
                : '🟡 Camera Online'
              : '🔴 Standby'}
          </span>
          <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary border border-primary/25">
            {liveState.mode_name || 'HUD Analytics'}
          </span>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Segmented Mode Toggle: Laptop Webcam vs Backend Stream */}
          <div className="inline-flex rounded-lg bg-slate-200/80 dark:bg-slate-800/80 p-0.5 border border-light-border dark:border-dark-border text-[11px] font-semibold">
            <button
              onClick={() => setStreamMode('browser')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
                streamMode === 'browser'
                  ? 'bg-primary text-white shadow-sm font-bold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Video className="h-3 w-3" />
              <span>Laptop Webcam</span>
            </button>
            <button
              onClick={() => setStreamMode('backend')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
                streamMode === 'backend'
                  ? 'bg-primary text-white shadow-sm font-bold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Cloud className="h-3 w-3" />
              <span>Backend Stream</span>
            </button>
          </div>

          {/* Toggle Landmarks Button */}
          <button
            onClick={() => setShowLandmarks(prev => !prev)}
            className={`p-1.5 rounded-lg border text-xs transition-colors ${
              showLandmarks
                ? 'bg-primary/10 text-primary border-primary/30'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-400 border-light-border dark:border-dark-border'
            }`}
            title={showLandmarks ? 'Hide hand landmarks' : 'Show hand landmarks'}
          >
            {showLandmarks ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
          </button>

          {/* Power Toggle Button */}
          <button
            onClick={() => {
              if (streamMode === 'browser') {
                browserCamReady ? stopBrowserWebcam() : startBrowserWebcam();
              } else {
                liveState.camera_active ? stopCamera(true) : startCamera(false);
              }
            }}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              (streamMode === 'browser' ? browserCamReady : liveState.camera_active)
                ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border-rose-500/30'
                : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 border-emerald-500/30 font-bold'
            }`}
          >
            {(streamMode === 'browser' ? browserCamReady : liveState.camera_active) ? (
              <CameraOff className="h-3.5 w-3.5" />
            ) : (
              <Camera className="h-3.5 w-3.5" />
            )}
            <span className="hidden sm:inline">
              {(streamMode === 'browser' ? browserCamReady : liveState.camera_active) ? 'Power Off' : 'Power On'}
            </span>
          </button>

          {/* Screenshot Snapshot Button */}
          <button
            onClick={handleScreenshot}
            disabled={capturing || !(streamMode === 'browser' ? browserCamReady : liveState.camera_active)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-light-border dark:border-dark-border text-xs font-semibold text-slate-700 dark:text-slate-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Capture screenshot"
          >
            {capturing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            ) : (
              <Camera className="h-3.5 w-3.5" />
            )}
            <span>Snapshot</span>
          </button>
        </div>
      </div>

      {/* Video Container (Aspect Ratio 16:9) */}
      <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
        {streamMode === 'browser' ? (
          // Mode 1: Browser Webcam (HTML5 getUserMedia)
          <div className="relative w-full h-full flex items-center justify-center">
            {/* Always mounted video element ensures videoRef is immediately available */}
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-contain -scale-x-100 transition-opacity duration-300 ${
                browserCamReady ? 'opacity-100' : 'opacity-0 absolute pointer-events-none'
              }`}
            />

            {/* Overlaid drawing & MediaPipe skeleton canvas */}
            <canvas
              ref={overlayCanvasRef}
              className={`absolute inset-0 w-full h-full pointer-events-none ${
                browserCamReady ? 'block' : 'hidden'
              }`}
            />

            {/* Standby / Permission UI when camera is not yet playing */}
            {!browserCamReady && (
              camPermissionError ? (
                <div className="flex flex-col items-center justify-center text-center p-6 sm:p-8">
                  <div className="h-14 sm:h-16 w-14 sm:w-16 rounded-2xl bg-rose-950/40 border border-rose-800/50 flex items-center justify-center mb-3 text-rose-400">
                    <CameraOff className="h-7 sm:h-8 w-7 sm:w-8" />
                  </div>
                  <h4 className="text-sm sm:text-base font-bold text-white mb-1">Camera Permission Blocked</h4>
                  <p className="text-xs text-slate-400 max-w-sm mb-4">
                    Your browser blocked webcam access. Please click the camera icon in your address bar to allow permissions, then click Retry.
                  </p>
                  <button
                    onClick={startBrowserWebcam}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold text-xs shadow-glow-primary transition-all"
                  >
                    <RefreshCw className="h-4 w-4" />
                    <span>Retry Camera Access</span>
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-6 sm:p-8">
                  <div className="h-14 sm:h-16 w-14 sm:w-16 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center mb-3 text-slate-400">
                    <CameraOff className="h-7 sm:h-8 w-7 sm:w-8" />
                  </div>
                  <h4 className="text-sm sm:text-base font-bold text-white mb-1">Webcam in Standby</h4>
                  <p className="text-xs text-slate-400 max-w-sm mb-4">
                    Click below to turn on your laptop's webcam.
                  </p>
                  <button
                    onClick={startBrowserWebcam}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold text-xs shadow-glow-primary transition-all"
                  >
                    <Camera className="h-4 w-4" />
                    <span>Turn Laptop Camera ON</span>
                  </button>
                </div>
              )
            )}
          </div>
        ) : (
          // Mode 2: Backend OpenCV Stream
          liveState.camera_active && !streamError ? (
            <img
              key={feedKey}
              src={videoUrl}
              alt="OmniGesture Live Feed"
              className="w-full h-full object-contain"
              loading="eager"
              onError={() => setStreamError(true)}
              onLoad={() => setStreamError(false)}
            />
          ) : (
            <div className="flex flex-col items-center justify-center text-center p-6 sm:p-8">
              <div className="h-14 sm:h-16 w-14 sm:w-16 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center mb-3 text-slate-400">
                <Cloud className="h-7 sm:h-8 w-7 sm:w-8" />
              </div>
              <h4 className="text-sm sm:text-base font-bold text-white mb-1">Backend Stream Standby</h4>
              <p className="text-xs text-slate-400 max-w-sm mb-4">
                Render cloud server has no physical camera attached. Switch to <strong>Laptop Webcam</strong> or run local backend via <code>run_backend.bat</code>.
              </p>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setStreamMode('browser')}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold text-xs shadow-glow-primary transition-all"
                >
                  <Video className="h-4 w-4" />
                  <span>Switch to Laptop Webcam</span>
                </button>
              </div>
            </div>
          )
        )}
      </div>

      {/* Feed Footer Bar */}
      <div className="px-4 sm:px-5 py-2.5 bg-slate-50/70 dark:bg-slate-900/60 border-t border-light-border dark:border-dark-border flex items-center justify-between text-[11px] sm:text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1.5 truncate">
          <Sparkles className="h-3.5 w-3.5 text-primary flex-shrink-0" />
          <span className="truncate">
            {streamMode === 'browser'
              ? 'Mode: Laptop Webcam + Real-time Cloud ML Inference'
              : 'Mode: Backend OpenCV MJPEG Stream'}
          </span>
        </span>
        <span className="font-mono text-accent flex-shrink-0 ml-2">
          FPS: {streamMode === 'browser' && browserCamReady ? '60.0' : (liveState.fps || '30.0')}
        </span>
      </div>
    </div>
  );
};
