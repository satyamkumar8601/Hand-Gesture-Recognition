import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Database,
  Play,
  Pause,
  PlusCircle,
  Trash2,
  Sparkles,
  Layers,
  AlertCircle,
  RefreshCw,
  Zap,
  Camera,
  Video,
  Cloud,
  CheckCircle2,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiUrl, getVideoFeedUrl } from '../config/api';

export const Dataset = () => {
  const { addNotification, liveState, startCamera, stopCamera } = useApp();
  const [gesturesList, setGesturesList] = useState([]);
  const [selectedGesture, setSelectedGesture] = useState('Thumbs Up');
  const [samplesSummary, setSamplesSummary] = useState({ total_samples: 0, samples_per_class: {} });
  const [targetSamples, setTargetSamples] = useState(100);
  const [isRecording, setIsRecording] = useState(false);
  const [burstCollecting, setBurstCollecting] = useState(false);

  // Cloud host detection
  const isCloudHost = typeof window !== 'undefined' &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1';

  const [streamMode, setStreamMode] = useState(isCloudHost ? 'browser' : 'backend');
  const [browserCamReady, setBrowserCamReady] = useState(false);

  const videoRef = useRef(null);
  const grabCanvasRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const recordingIntervalRef = useRef(null);

  // Manage browser webcam
  const startBrowserCam = useCallback(async () => {
    try {
      if (mediaStreamRef.current && mediaStreamRef.current.active) {
        if (videoRef.current && videoRef.current.srcObject !== mediaStreamRef.current) {
          videoRef.current.srcObject = mediaStreamRef.current;
          videoRef.current.play().catch(() => {});
        }
        setBrowserCamReady(true);
        return;
      }

      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
          audio: false,
        });
        mediaStreamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
        setBrowserCamReady(true);
      }
    } catch (e) {
      console.warn('Webcam start error in Dataset studio:', e);
      setBrowserCamReady(false);
    }
  }, []);

  const stopBrowserCam = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setBrowserCamReady(false);
  }, []);

  // Handle stream mode switches
  useEffect(() => {
    if (streamMode === 'browser') {
      stopCamera(true);
      startBrowserCam();
      return () => {
        stopBrowserCam();
      };
    } else {
      stopBrowserCam();
      startCamera(true);
      return () => {
        stopCamera(true);
      };
    }
  }, [streamMode, startBrowserCam, stopBrowserCam, startCamera, stopCamera]);

  // Fetch gestures catalog
  useEffect(() => {
    fetch(apiUrl('/api/gestures/list'))
      .then(res => res.json())
      .then(data => {
        if (data.all_gestures) {
          setGesturesList(data.all_gestures);
          if (data.all_gestures.length > 0) setSelectedGesture(data.all_gestures[0]);
        }
      })
      .catch(() => {});

    refreshDataset();
  }, []);

  const refreshDataset = async () => {
    try {
      const res = await fetch(apiUrl('/api/dataset/summary'));
      if (res.ok) {
        const data = await res.json();
        setSamplesSummary(data);
      }
    } catch (e) {
      console.error('Failed to load dataset summary:', e);
    }
  };

  // Helper to grab frame from laptop webcam as base64 JPEG
  const grabCurrentFrameBase64 = () => {
    if (streamMode === 'browser' && videoRef.current && grabCanvasRef.current) {
      const video = videoRef.current;
      if (video.videoWidth > 0 && video.videoHeight > 0) {
        const canvas = grabCanvasRef.current;
        canvas.width = 480;
        canvas.height = Math.round((480 * video.videoHeight) / video.videoWidth);
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/jpeg', 0.85);
      }
    }
    return null;
  };

  const captureSingleSample = async () => {
    const b64 = grabCurrentFrameBase64();
    const payload = { gesture_name: selectedGesture, count: 1 };
    if (b64) payload.image_base64 = b64;

    try {
      const res = await fetch(apiUrl('/api/dataset/collect'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        addNotification(data.message, 'success');
        refreshDataset();
      } else {
        addNotification(data.message || 'Capture failed', 'error');
      }
    } catch (e) {
      addNotification('Error collecting sample', 'error');
    }
  };

  const captureBurstSamples = async () => {
    if (burstCollecting) return;
    setBurstCollecting(true);
    const b64 = grabCurrentFrameBase64();
    const payload = { gesture_name: selectedGesture, count: 10 };
    if (b64) payload.image_base64 = b64;

    try {
      const res = await fetch(apiUrl('/api/dataset/collect_batch'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        addNotification(data.message, 'success');
        refreshDataset();
      } else {
        addNotification(data.message || 'Burst capture failed', 'error');
      }
    } catch (e) {
      addNotification('Error collecting burst samples', 'error');
    } finally {
      setBurstCollecting(false);
    }
  };

  // Continuous collection loop with local optimistic count and debounced summary refresh
  useEffect(() => {
    if (isRecording) {
      recordingIntervalRef.current = setInterval(async () => {
        const b64 = grabCurrentFrameBase64();
        const payload = { gesture_name: selectedGesture, count: 1 };
        if (b64) payload.image_base64 = b64;

        try {
          const res = await fetch(apiUrl('/api/dataset/collect'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const data = await res.json();
          if (data.success) {
            setSamplesSummary(prev => {
              const perClass = { ...(prev.samples_per_class || {}) };
              perClass[selectedGesture] = (perClass[selectedGesture] || 0) + 1;
              return {
                ...prev,
                total_samples: (prev.total_samples || 0) + 1,
                samples_per_class: perClass,
              };
            });
          }
        } catch (e) {}
      }, 250);
    } else {
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
      refreshDataset();
    }

    return () => {
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
    };
  }, [isRecording, selectedGesture]);

  const handleDeleteClass = async (gestureName) => {
    if (!window.confirm(`Are you sure you want to delete all recorded samples for '${gestureName}'?`)) {
      return;
    }

    try {
      const res = await fetch(apiUrl(`/api/dataset/${encodeURIComponent(gestureName)}`), {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        addNotification(`Deleted ${data.deleted_count} samples of '${gestureName}'`, 'info');
        refreshDataset();
      }
    } catch (e) {
      addNotification('Failed to delete class samples', 'error');
    }
  };

  const currentCount = samplesSummary.samples_per_class?.[selectedGesture] || 0;
  const progressPct = Math.min(100, Math.round((currentCount / targetSamples) * 100));

  return (
    <div className="space-y-6 sm:space-y-8 w-full">
      <canvas ref={grabCanvasRef} className="hidden" />

      {/* Studio Header Card */}
      <div className="glass-card rounded-3xl p-5 sm:p-8 border border-light-border dark:border-dark-border">
        <div className="max-w-2xl space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/15 text-primary text-xs font-bold uppercase tracking-wider">
            <Sparkles className="h-3.5 w-3.5" />
            Landmark Dataset Collection Studio
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white brand-font">
            Capture Real-Time Hand Training Samples
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Select a target gesture, position your hand in front of the webcam, and capture landmark feature vectors into your training dataset.
          </p>
        </div>

        {/* Collection Controls Bar */}
        <div className="mt-6 p-6 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-light-border dark:border-dark-border grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 items-end">
          {/* Gesture Selector */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
              Select Gesture
            </label>
            <select
              value={selectedGesture}
              onChange={(e) => {
                setIsRecording(false);
                setSelectedGesture(e.target.value);
              }}
              className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-sm font-semibold text-slate-800 dark:text-white focus:ring-2 focus:ring-primary outline-none"
            >
              {gesturesList.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>

          {/* Target Sample Count */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
              Target Samples
            </label>
            <input
              type="number"
              min="10"
              max="2000"
              step="50"
              value={targetSamples}
              onChange={(e) => setTargetSamples(Math.max(10, parseInt(e.target.value) || 100))}
              className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-sm font-semibold text-slate-800 dark:text-white focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          {/* Continuous Recording Toggle */}
          <div>
            <button
              onClick={() => setIsRecording(prev => !prev)}
              className={`w-full py-2.5 px-3.5 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 border transition-all duration-200 shadow-md ${
                isRecording
                  ? 'bg-rose-500 hover:bg-rose-600 text-white border-rose-600 animate-pulse'
                  : 'bg-accent hover:bg-accent-hover text-white border-accent shadow-glow-accent'
              }`}
            >
              {isRecording ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              <span>{isRecording ? 'Pause Loop' : 'Auto Stream'}</span>
            </button>
          </div>

          {/* Single Sample Capture Button */}
          <div>
            <button
              onClick={captureSingleSample}
              disabled={isRecording}
              className="w-full py-2.5 px-3.5 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 bg-primary hover:bg-primary-hover disabled:opacity-50 text-white border border-primary transition-all duration-200 shadow-glow-primary cursor-pointer"
            >
              <PlusCircle className="h-4 w-4" />
              <span>Capture 1 Sample</span>
            </button>
          </div>

          {/* Burst 10 Samples Capture Button */}
          <div>
            <button
              onClick={captureBurstSamples}
              disabled={isRecording || burstCollecting}
              className="w-full py-2.5 px-3.5 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 bg-gradient-to-r from-secondary to-indigo-600 hover:opacity-90 disabled:opacity-50 text-white border border-secondary transition-all duration-200 shadow-md cursor-pointer"
            >
              {burstCollecting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4 text-cyber-cyan" />}
              <span>{burstCollecting ? 'Collecting...' : '⚡ Burst 10 Samples'}</span>
            </button>
          </div>
        </div>

        {/* Live Studio Camera Preview Visualizer */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4 items-center p-4 rounded-2xl bg-slate-950 border border-slate-800 shadow-inner">
          <div className="lg:col-span-2 relative aspect-video rounded-xl overflow-hidden bg-black border border-slate-800 shadow-lg flex items-center justify-center">
            {streamMode === 'browser' ? (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-contain -scale-x-100"
              />
            ) : (
              <img
                src={getVideoFeedUrl(true) || ''}
                alt="Live Dataset Studio Feed"
                className="w-full h-full object-contain"
              />
            )}

            {/* Top Badge: Mode Switcher & Hand Active indicator */}
            <div className="absolute top-2 left-2 right-2 flex items-center justify-between pointer-events-auto">
              <div className="px-2.5 py-1 rounded-md bg-black/70 backdrop-blur-md text-[10px] font-bold text-cyber-cyan border border-white/10 flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${liveState.hand_detected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
                <span>{liveState.hand_detected ? `Hand Active (${liveState.primary_gesture})` : 'Position Hand in View'}</span>
              </div>

              {/* Source Switcher */}
              <div className="inline-flex rounded-lg bg-black/80 backdrop-blur-md p-0.5 border border-white/10 text-[10px] font-semibold">
                <button
                  onClick={() => setStreamMode('browser')}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded transition-all ${
                    streamMode === 'browser'
                      ? 'bg-primary text-white font-bold'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Video className="h-2.5 w-2.5" />
                  <span>Laptop</span>
                </button>
                <button
                  onClick={() => setStreamMode('backend')}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded transition-all ${
                    streamMode === 'backend'
                      ? 'bg-primary text-white font-bold'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Cloud className="h-2.5 w-2.5" />
                  <span>Backend</span>
                </button>
              </div>
            </div>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Detected Live Pose</span>
              <span className="text-base font-extrabold text-white mt-0.5 block">{liveState.primary_gesture || 'No Hand'}</span>
              <span className="text-[11px] text-slate-400 font-mono">Confidence: {liveState.confidence || 0}%</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Target Training Class</span>
              <span className="text-sm font-extrabold text-accent mt-0.5 block">{selectedGesture}</span>
            </div>
            <div className="p-3 rounded-xl bg-primary/10 border border-primary/25 text-[11px] text-slate-300">
              💡 <strong>Instant Capture:</strong> Position hand, verify skeletal tracking above, and click <strong>Capture 1 Sample</strong> or <strong>Burst 10 Samples</strong>!
            </div>
          </div>
        </div>

        {/* Live Progress Bar for Selected Class */}
        <div className="mt-6 p-5 rounded-2xl bg-white/50 dark:bg-slate-800/40 border border-light-border dark:border-dark-border">
          <div className="flex items-center justify-between text-xs font-bold mb-2">
            <span className="text-slate-700 dark:text-slate-300">
              Collection Progress ({selectedGesture})
            </span>
            <span className="font-mono text-primary font-black text-sm">
              {currentCount} / {targetSamples} Samples ({progressPct}%)
            </span>
          </div>
          <div className="h-3 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-300 dark:border-slate-700">
            <div
              className="h-full bg-gradient-to-r from-primary to-accent rounded-full transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Dataset Overview Grid for All 17 Classes */}
      <div className="glass-card rounded-3xl p-6 sm:p-8 border border-light-border dark:border-dark-border">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="text-xl font-black text-slate-900 dark:text-white brand-font flex items-center gap-2">
              <Layers className="h-5 w-5 text-primary" />
              <span>Dataset Class Distribution</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Total Recorded Samples: <strong>{samplesSummary.total_samples || 0}</strong> across {gesturesList.length} classes
            </p>
          </div>

          <button
            onClick={refreshDataset}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-xs font-bold text-slate-700 dark:text-slate-200 border border-light-border dark:border-dark-border transition-colors self-start sm:self-auto"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refresh Counts</span>
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {gesturesList.map((gestureName) => {
            const count = samplesSummary.samples_per_class?.[gestureName] || 0;
            const isSelected = selectedGesture === gestureName;
            return (
              <div
                key={gestureName}
                onClick={() => setSelectedGesture(gestureName)}
                className={`p-3.5 rounded-2xl border transition-all duration-200 cursor-pointer text-center relative group ${
                  isSelected
                    ? 'bg-primary/10 border-primary shadow-glow-primary scale-[1.02]'
                    : 'bg-slate-50 dark:bg-slate-900/50 hover:bg-slate-100 dark:hover:bg-slate-800/80 border-light-border dark:border-dark-border'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-[10px] font-bold uppercase tracking-wider ${isSelected ? 'text-primary' : 'text-slate-400'}`}>
                    {count >= 50 ? 'Balanced' : 'Needs Data'}
                  </span>
                  {count > 0 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteClass(gestureName);
                      }}
                      className="opacity-0 group-hover:opacity-100 text-rose-500 hover:text-rose-600 transition-opacity p-0.5"
                      title={`Clear all ${gestureName} samples`}
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                </div>

                <div className="text-xs font-extrabold text-slate-800 dark:text-white truncate mb-1" title={gestureName}>
                  {gestureName}
                </div>

                <div className="text-base font-black font-mono text-primary">
                  {count}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
