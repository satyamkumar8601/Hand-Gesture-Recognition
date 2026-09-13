import React, { useState, useEffect } from 'react';
import { Camera, CameraOff, Sparkles, Eye, EyeOff, Loader2, RefreshCw, ServerOff, Settings as SettingsIcon } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiUrl, getVideoFeedUrl } from '../config/api';

export const CameraFeed = () => {
  const { liveState, startCamera, stopCamera, addNotification, setActivePage, backendStatus } = useApp();
  const [showLandmarks, setShowLandmarks] = useState(true);
  const [capturing, setCapturing] = useState(false);
  const [feedKey, setFeedKey] = useState(() => Date.now());
  const [streamError, setStreamError] = useState(false);

  const videoUrl = getVideoFeedUrl(showLandmarks, feedKey);

  // Auto-start camera hardware when component mounts, and auto-release when unmounting
  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  useEffect(() => {
    if (liveState.camera_active) {
      setStreamError(false);
    }
  }, [liveState.camera_active]);

  const handleRetry = () => {
    setStreamError(false);
    setFeedKey(Date.now());
    startCamera();
  };

  const handleScreenshot = async () => {
    if (capturing) return;
    setCapturing(true);
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
      {/* Feed Top Controls (Responsive flex-wrap) */}
      <div className="px-3 sm:px-5 py-3 border-b border-light-border dark:border-dark-border flex flex-wrap items-center justify-between gap-2.5 bg-slate-50/50 dark:bg-slate-900/40">
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${
              liveState.camera_active
                ? liveState.hand_detected
                  ? 'bg-accent shadow-glow-accent animate-pulse'
                  : 'bg-emerald-400'
                : 'bg-rose-500'
            }`}
          />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
            {liveState.camera_active
              ? liveState.hand_detected
                ? `🟢 Hand Active (${liveState.hands_count})`
                : '🟡 Feed Online (No Hand)'
              : '🔴 Hardware Standby'}
          </span>
          <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary border border-primary/25">
            {liveState.mode_name || 'HUD Analytics'}
          </span>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Quick Power Toggle */}
          <button
            onClick={liveState.camera_active ? stopCamera : startCamera}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              liveState.camera_active
                ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border-rose-500/30'
                : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 border-emerald-500/30 font-bold'
            }`}
            title={liveState.camera_active ? 'Turn webcam hardware OFF' : 'Turn webcam hardware ON'}
          >
            {liveState.camera_active ? <CameraOff className="h-3.5 w-3.5" /> : <Camera className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{liveState.camera_active ? 'Power Off' : 'Power On'}</span>
          </button>
          {/* Toggle Landmarks Button */}
          <button
            onClick={() => setShowLandmarks(prev => !prev)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              showLandmarks
                ? 'bg-primary/15 border-primary/40 text-primary'
                : 'bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-500'
            }`}
            title="Toggle skeletal landmark overlay"
          >
            {showLandmarks ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
            <span>Landmarks</span>
          </button>

          {/* Screenshot Button */}
          <button
            onClick={handleScreenshot}
            disabled={capturing || !liveState.camera_active}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-light-border dark:border-dark-border text-xs font-semibold text-slate-700 dark:text-slate-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Capture annotated screenshot"
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
        {videoUrl === null ? (
          <div className="flex flex-col items-center justify-center text-center p-6 sm:p-8">
            <div className="h-14 sm:h-16 w-14 sm:w-16 rounded-2xl bg-amber-950/40 border border-amber-800/50 flex items-center justify-center mb-3 text-amber-400">
              <ServerOff className="h-7 sm:h-8 w-7 sm:w-8" />
            </div>
            <h4 className="text-sm sm:text-base font-bold text-white mb-1">Backend Server Not Configured</h4>
            <p className="text-xs text-slate-400 max-w-md mb-4">
              You are running the frontend in the cloud. To view live camera inference or run local models, deploy your backend or connect via local tunnel.
            </p>
            <button
              onClick={() => setActivePage('settings')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold text-xs shadow-glow-primary transition-all duration-200"
            >
              <SettingsIcon className="h-4 w-4" />
              <span>Configure Backend in Settings</span>
            </button>
          </div>
        ) : liveState.camera_active && !streamError ? (
          <img
            key={feedKey}
            src={videoUrl}
            alt="OmniGesture Live Feed"
            className="w-full h-full object-contain"
            loading="eager"
            onError={() => {
              console.warn("MJPEG stream error or disconnect detected");
              setStreamError(true);
            }}
            onLoad={() => {
              setStreamError(false);
            }}
          />
        ) : streamError ? (
          <div className="flex flex-col items-center justify-center text-center p-6 sm:p-8">
            <div className="h-14 sm:h-16 w-14 sm:w-16 rounded-2xl bg-rose-950/40 border border-rose-800/50 flex items-center justify-center mb-3 text-rose-400">
              <CameraOff className="h-7 sm:h-8 w-7 sm:w-8" />
            </div>
            <h4 className="text-sm sm:text-base font-bold text-white mb-1">Camera Stream Disconnected</h4>
            <p className="text-xs text-slate-400 max-w-sm mb-4">
              The camera feed was interrupted or device is initializing. Click below to reconnect.
            </p>
            <button
              onClick={handleRetry}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold text-xs shadow-glow-primary transition-all duration-200"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Reconnect Camera</span>
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center p-6 sm:p-8">
            <div className="h-14 sm:h-16 w-14 sm:w-16 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center mb-3 sm:mb-4 text-slate-400">
              <CameraOff className="h-7 sm:h-8 w-7 sm:w-8" />
            </div>
            <h4 className="text-sm sm:text-base font-bold text-white mb-1">Camera is in Standby Mode</h4>
            <p className="text-xs text-slate-400 max-w-sm mb-4 sm:mb-5">
              The webcam hardware is currently powered down to preserve energy, prevent heating, and guarantee privacy.
            </p>
            <button
              onClick={startCamera}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold text-xs shadow-glow-primary transition-all duration-200 transform hover:scale-105 active:scale-95"
            >
              <Camera className="h-4 w-4" />
              <span>Turn Camera ON</span>
            </button>
          </div>
        )}
      </div>

      {/* Feed Footer Bar */}
      <div className="px-4 sm:px-5 py-2.5 bg-slate-50/70 dark:bg-slate-900/60 border-t border-light-border dark:border-dark-border flex items-center justify-between text-[11px] sm:text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1.5 truncate">
          <Sparkles className="h-3.5 w-3.5 text-primary flex-shrink-0" />
          <span className="truncate">Engine: MediaPipe 3D Landmarker (21 Spatial Nodes)</span>
        </span>
        <span className="font-mono text-accent flex-shrink-0 ml-2">FPS: {liveState.fps || '30.0'}</span>
      </div>
    </div>
  );
};
