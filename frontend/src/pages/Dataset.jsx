import React, { useState, useEffect, useRef } from 'react';
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
  const [loading, setLoading] = useState(false);

  const recordingIntervalRef = useRef(null);

  // Auto-start camera when entering Dataset Studio so collection works instantly
  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

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

  const captureSingleSample = async () => {
    try {
      const res = await fetch(apiUrl('/api/dataset/collect'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gesture_name: selectedGesture, count: 1 }),
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
    try {
      const res = await fetch(apiUrl('/api/dataset/collect_batch'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gesture_name: selectedGesture, count: 10 }),
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
        try {
          const res = await fetch(apiUrl('/api/dataset/collect'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gesture_name: selectedGesture, count: 1 }),
          });
          const data = await res.json();
          if (data.success) {
            // Instant local state update for zero lag
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
      }, 140);
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
            >
            </input>
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
              className="w-full py-2.5 px-3.5 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 bg-primary hover:bg-primary-hover disabled:opacity-50 text-white border border-primary transition-all duration-200 shadow-glow-primary"
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
          <div className="lg:col-span-2 relative aspect-video rounded-xl overflow-hidden bg-black border border-slate-800 shadow-lg">
            <img
              src={getVideoFeedUrl(true) || ''}
              alt="Live Dataset Studio Feed"
              className="w-full h-full object-contain"
            />
            <div className="absolute top-2 left-2 px-2.5 py-1 rounded-md bg-black/70 backdrop-blur-md text-[10px] font-bold text-cyber-cyan border border-white/10 flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${liveState.hand_detected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
              <span>{liveState.hand_detected ? `Hand Active (${liveState.primary_gesture})` : 'Position Hand in Frame'}</span>
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
      <div className="glass-card rounded-3xl p-8 border border-light-border dark:border-dark-border">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-black text-slate-900 dark:text-white brand-font">
              Dataset Breakdown by Gesture Class
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Total Dataset Size: <strong className="text-accent font-mono">{samplesSummary.total_samples}</strong> landmark feature samples recorded
            </p>
          </div>

          <button
            onClick={refreshDataset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-light-border dark:border-dark-border text-xs font-semibold text-slate-700 dark:text-slate-200"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3.5">
          {gesturesList.map((gesture) => {
            const count = samplesSummary.samples_per_class?.[gesture] || 0;
            const isSelected = selectedGesture === gesture;
            return (
              <div
                key={gesture}
                onClick={() => setSelectedGesture(gesture)}
                className={`p-3.5 rounded-2xl border cursor-pointer transition-all duration-200 relative group flex flex-col justify-between ${
                  isSelected
                    ? 'bg-primary/10 border-primary shadow-glow-primary'
                    : 'bg-slate-50 dark:bg-slate-800/60 border-light-border dark:border-dark-border hover:border-slate-400'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 dark:text-white truncate">
                      {gesture}
                    </span>
                    {count > 0 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteClass(gesture);
                        }}
                        className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-500 transition-opacity p-0.5"
                        title={`Delete ${gesture} samples`}
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Samples</span>
                  <span
                    className={`text-xs font-mono font-bold px-2 py-0.5 rounded-md ${
                      count > 0
                        ? 'bg-accent/15 text-accent border border-accent/30'
                        : 'bg-slate-200 dark:bg-slate-700 text-slate-500'
                    }`}
                  >
                    {count}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
