import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Camera, CameraOff, Sparkles, Eye, EyeOff, Loader2, RefreshCw, Video, Cloud, Download } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiUrl, getVideoFeedUrl } from '../config/api';

export const CameraFeed = () => {
  const {
    liveState,
    setLiveState,
    startCamera,
    stopCamera,
    addNotification,
    voiceEnabled,
    speakGesture,
    addGestureToSentence,
  } = useApp();

  const [showLandmarks, setShowLandmarks] = useState(true);
  const [capturing, setCapturing] = useState(false);
  const [feedKey, setFeedKey] = useState(() => Date.now());
  const [streamError, setStreamError] = useState(false);

  // Dual-mode: Browser Webcam (HTML5 getUserMedia) vs Backend Stream (OpenCV /video_feed)
  // Default to browser webcam on cloud/Vercel so user immediately sees their own camera!
  const isCloud = typeof window !== 'undefined' &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1';

  const [useBrowserCam, setUseBrowserCam] = useState(isCloud);
  const [browserCamActive, setBrowserCamActive] = useState(false);
  const [permissionDenied, setPermissionDenied] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const pollTimerRef = useRef(null);
  const isPredictingRef = useRef(false);

  const videoUrl = getVideoFeedUrl(showLandmarks, feedKey);

  // 1. Browser Webcam Stream Setup
  const startBrowserCam = useCallback(async () => {
    setPermissionDenied(false);
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => {});
        }
        setBrowserCamActive(true);
        setLiveState(prev => ({ ...prev, camera_active: true }));
        addNotification('Browser camera connected', 'success');
      } else {
        setPermissionDenied(true);
        addNotification('Webcam API not supported in this browser', 'error');
      }
    } catch (err) {
      console.warn('Webcam permission error:', err);
      setPermissionDenied(true);
      setBrowserCamActive(false);
      addNotification('Camera access denied. Please allow webcam permission in browser.', 'error');
    }
  }, [addNotification, setLiveState]);

  const stopBrowserCam = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setBrowserCamActive(false);
    setLiveState(prev => ({ ...prev, camera_active: false }));
  }, [setLiveState]);

  // Manage camera based on mode
  useEffect(() => {
    if (useBrowserCam) {
      startBrowserCam();
      return () => {
        stopBrowserCam();
      };
    } else {
      startCamera();
      return () => {
        stopCamera();
      };
    }
  }, [useBrowserCam, startBrowserCam, stopBrowserCam, startCamera, stopCamera]);

  // Periodic frame inference when using Browser Webcam
  useEffect(() => {
    if (!useBrowserCam || !browserCamActive) return;

    const interval = setInterval(async () => {
      if (isPredictingRef.current || !videoRef.current || !canvasRef.current) return;
      const video = videoRef.current;
      if (video.readyState < 2 || video.videoWidth === 0) return;

      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      canvas.width = 320;
      canvas.height = 240;
      ctx.drawImage(video, 0, 0, 320, 240);

      const b64 = canvas.toDataURL('image/jpeg', 0.5);
      isPredictingRef.current = true;

      try {
        const res = await fetch(apiUrl('/api/predict/frame'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_base64: b64 }),
        });
        if (res.ok) {
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
            }));
            if (voiceEnabled && data.primary_gesture) {
              speakGesture(data.primary_gesture);
            }
          } else {
            setLiveState(prev => ({
              ...prev,
              hand_detected: false,
              hands_count: 0,
              primary_gesture: 'No Hand',
              confidence: 0,
              camera_active: true,
            }));
          }
        }
      } catch (err) {
        // Backend ping failed; keep streaming locally
      } finally {
        isPredictingRef.current = false;
      }
    }, 220);

    return () => clearInterval(interval);
  }, [useBrowserCam, browserCamActive, setLiveState, voiceEnabled, speakGesture]);

  const handleScreenshot = async () => {
    if (capturing) return;
    setCapturing(true);

    if (useBrowserCam && videoRef.current) {
      // Local client-side high-res frame capture
      try {
        const video = videoRef.current;
        const snapCanvas = document.createElement('canvas');
        snapCanvas.width = video.videoWidth || 640;
        snapCanvas.height = video.videoHeight || 480;
        const sctx = snapCanvas.getContext('2d');
        // Mirror horizontally
        sctx.translate(snapCanvas.width, 0);
        sctx.scale(-1, 1);
        sctx.drawImage(video, 0, 0, snapCanvas.width, snapCanvas.height);

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

    // Backend Stream snapshot
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
      {/* Hidden processing canvas for frame prediction */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Feed Top Controls */}
      <div className="px-3 sm:px-5 py-3 border-b border-light-border dark:border-dark-border flex flex-wrap items-center justify-between gap-2.5 bg-slate-50/50 dark:bg-slate-900/40">
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${
              (useBrowserCam ? browserCamActive : liveState.camera_active)
                ? liveState.hand_detected
                  ? 'bg-accent shadow-glow-accent animate-pulse'
                  : 'bg-emerald-400'
                : 'bg-rose-500'
            }`}
          />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
            {(useBrowserCam ? browserCamActive : liveState.camera_active)
              ? liveState.hand_detected
                ? `🟢 Hand Active (${liveState.hands_count || 1})`
                : '🟡 Camera Online (Show Hand)'
              : '🔴 Standby'}
          </span>
          <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary border border-primary/25">
            {useBrowserCam ? '📹 Browser Cam' : '☁️ Backend Stream'}
          </span>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Stream Source Toggle: Browser Cam vs Cloud/Backend Feed */}
          <button
            onClick={() => {
              if (useBrowserCam) {
                stopBrowserCam();
                setUseBrowserCam(false);
              } else {
                setUseBrowserCam(true);
              }
            }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border border-light-border dark:border-dark-border bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            title="Switch between in-browser webcam and server feed"
          >
            {useBrowserCam ? <Cloud className="h-3.5 w-3.5 text-cyan-400" /> : <Video className="h-3.5 w-3.5 text-emerald-400" />}
            <span>{useBrowserCam ? 'Backend Stream' : 'Browser Cam'}</span>
          </button>

          {/* Quick Power Toggle */}
          <button
            onClick={() => {
              if (useBrowserCam) {
                browserCamActive ? stopBrowserCam() : startBrowserCam();
              } else {
                liveState.camera_active ? stopCamera() : startCamera();
              }
            }}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              (useBrowserCam ? browserCamActive : liveState.camera_active)
                ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border-rose-500/30'
                : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 border-emerald-500/30 font-bold'
            }`}
          >
            {(useBrowserCam ? browserCamActive : liveState.camera_active) ? (
              <CameraOff className="h-3.5 w-3.5" />
            ) : (
              <Camera className="h-3.5 w-3.5" />
            )}
            <span className="hidden sm:inline">
              {(useBrowserCam ? browserCamActive : liveState.camera_active) ? 'Power Off' : 'Power On'}
            </span>
          </button>

          {/* Screenshot Button */}
          <button
            onClick={handleScreenshot}
            disabled={capturing || !(useBrowserCam ? browserCamActive : liveState.camera_active)}
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
        {useBrowserCam ? (
          // In-Browser HTML5 Local Camera Mode
          browserCamActive ? (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-contain -scale-x-100"
            />
          ) : permissionDenied ? (
            <div className="flex flex-col items-center justify-center text-center p-6 sm:p-8">
              <div className="h-14 sm:h-16 w-14 sm:w-16 rounded-2xl bg-amber-950/40 border border-amber-800/50 flex items-center justify-center mb-3 text-amber-400">
                <CameraOff className="h-7 sm:h-8 w-7 sm:w-8" />
              </div>
              <h4 className="text-sm sm:text-base font-bold text-white mb-1">Webcam Permission Required</h4>
              <p className="text-xs text-slate-400 max-w-sm mb-4">
                Please allow camera access in your browser to enable live hand gesture recognition.
              </p>
              <button
                onClick={startBrowserCam}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold text-xs shadow-glow-primary transition-all duration-200"
              >
                <RefreshCw className="h-4 w-4" />
                <span>Grant Camera Permission</span>
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center text-center p-6 sm:p-8">
              <div className="h-14 sm:h-16 w-14 sm:w-16 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center mb-3 sm:mb-4 text-slate-400">
                <CameraOff className="h-7 sm:h-8 w-7 sm:w-8" />
              </div>
              <h4 className="text-sm sm:text-base font-bold text-white mb-1">Webcam in Standby</h4>
              <p className="text-xs text-slate-400 max-w-sm mb-4">
                Click below to start your browser camera and begin gesture detection.
              </p>
              <button
                onClick={startBrowserCam}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold text-xs shadow-glow-primary transition-all duration-200"
              >
                <Camera className="h-4 w-4" />
                <span>Turn Camera ON</span>
              </button>
            </div>
          )
        ) : (
          // Backend MJPEG Stream Mode
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
                <CameraOff className="h-7 sm:h-8 w-7 sm:w-8" />
              </div>
              <h4 className="text-sm sm:text-base font-bold text-white mb-1">Backend Stream Standby</h4>
              <p className="text-xs text-slate-400 max-w-sm mb-4">
                Click below or switch to Browser Cam to stream your laptop webcam.
              </p>
              <div className="flex items-center gap-3">
                <button
                  onClick={startCamera}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold text-xs shadow-glow-primary transition-all"
                >
                  <Camera className="h-4 w-4" />
                  <span>Start Backend Camera</span>
                </button>
                <button
                  onClick={() => setUseBrowserCam(true)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white font-semibold text-xs transition-all"
                >
                  <Video className="h-4 w-4 text-emerald-400" />
                  <span>Switch to Browser Cam</span>
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
            {useBrowserCam ? 'Direct Browser Camera & AI Cloud Inference' : 'Engine: MediaPipe 3D Landmarker'}
          </span>
        </span>
        <span className="font-mono text-accent flex-shrink-0 ml-2">
          FPS: {useBrowserCam && browserCamActive ? '30.0' : (liveState.fps || '30.0')}
        </span>
      </div>
    </div>
  );
};
