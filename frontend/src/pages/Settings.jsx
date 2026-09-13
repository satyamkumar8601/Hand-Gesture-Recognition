import React, { useState, useEffect } from 'react';
import { 
  Sliders, 
  Camera, 
  Cpu, 
  ShieldCheck, 
  Save, 
  RotateCcw, 
  CheckCircle2, 
  Info, 
  Command, 
  Eye, 
  EyeOff, 
  Server,
  Zap,
  Layers,
  Globe,
  Activity,
  Check,
  X,
  RefreshCw
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiUrl, getApiBaseUrl, getCustomApiUrl, setCustomApiUrl, clearCustomApiUrl, checkBackendHealth } from '../config/api';

export const Settings = () => {
  const { addNotification, refreshModelInfo, modelInfo, liveState, startCamera, stopCamera } = useApp();

  const [customBackendUrl, setCustomBackendUrl] = useState(() => getCustomApiUrl());
  const [testingBackend, setTestingBackend] = useState(false);
  const [backendTestResult, setBackendTestResult] = useState(null);

  const [settings, setSettings] = useState({
    camera_index: 0,
    resolution: '640x480',
    fps: 30,
    auto_off_timeout: 5,
    min_detection_confidence: 0.65,
    min_tracking_confidence: 0.60,
    recognition_threshold: 0.70,
    smoothing_alpha: 0.65,
    inference_mode: 'hybrid', // 'hybrid' or 'rule_only'
    show_skeleton_overlay: true,
    show_fps_hud: true,
  });

  const [saving, setSaving] = useState(false);
  const [reloadingModel, setReloadingModel] = useState(false);

  // Load existing settings from backend on mount
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await fetch(apiUrl('/api/settings'));
        if (res.ok) {
          const data = await res.json();
          setSettings(prev => ({ ...prev, ...data }));
        }
      } catch (e) {
        console.error('Failed to load settings from server:', e);
      }
    };
    fetchSettings();
  }, []);

  const handleChange = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch(apiUrl('/api/settings'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        addNotification('Configuration saved successfully to SQLite database', 'success');
      } else {
        addNotification('Failed to save settings on server', 'error');
      }
    } catch (e) {
      addNotification('Server connection error while saving', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setSettings({
      camera_index: 0,
      resolution: '640x480',
      fps: 30,
      auto_off_timeout: 5,
      min_detection_confidence: 0.65,
      min_tracking_confidence: 0.60,
      recognition_threshold: 0.70,
      smoothing_alpha: 0.65,
      inference_mode: 'hybrid',
      show_skeleton_overlay: true,
      show_fps_hud: true,
    });
    addNotification('Settings reset to system factory defaults', 'info');
  };

  const handleHotReloadModel = async () => {
    setReloadingModel(true);
    try {
      const res = await fetch(apiUrl('/api/model/reload'), { method: 'POST' });
      if (res.ok) {
        await refreshModelInfo();
        addNotification('Machine learning model pipeline reloaded from disk!', 'success');
      } else {
        addNotification('Could not reload model', 'error');
      }
    } catch (e) {
      addNotification('Connection failed while reloading model', 'error');
    } finally {
      setReloadingModel(false);
    }
  };

  const handleTestBackend = async (urlToTest = customBackendUrl) => {
    setTestingBackend(true);
    setBackendTestResult(null);
    try {
      const res = await checkBackendHealth(urlToTest);
      setBackendTestResult(res);
      if (res.ok) {
        addNotification(`Backend Online (${res.latency}ms latency)`, 'success');
      } else {
        addNotification(`Backend Connection Failed: ${res.error}`, 'error');
      }
    } catch (e) {
      setBackendTestResult({ ok: false, error: 'Network error' });
    } finally {
      setTestingBackend(false);
    }
  };

  const handleSaveBackendUrl = () => {
    setCustomApiUrl(customBackendUrl);
    handleTestBackend(customBackendUrl);
    addNotification('Backend URL saved and applied across app', 'info');
  };

  const handleResetBackendUrl = () => {
    clearCustomApiUrl();
    setCustomBackendUrl('');
    handleTestBackend('');
    addNotification('Reverted to default backend configuration', 'info');
  };

  return (
    <div className="space-y-6 sm:space-y-8 animate-fadeIn w-full pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyber-border/40 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 text-cyan-400">
              <Sliders className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">System Settings</h1>
              <p className="text-slate-400 text-xs sm:text-sm">Fine-tune hardware capture, MediaPipe tracking thresholds, and ML inference behavior.</p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-cyber-border/60 bg-cyber-card/60 hover:bg-cyber-card text-slate-300 text-sm font-medium transition-all"
          >
            <RotateCcw className="w-4 h-4 text-slate-400" />
            Reset Defaults
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm shadow-lg shadow-cyan-500/20 transition-all disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Columns: Settings Controls */}
        <div className="lg:col-span-2 space-y-8">
          {/* Section 0: Cloud & Backend API Connectivity */}
          <div className="p-6 rounded-2xl bg-cyber-card/80 border border-cyber-border/60 backdrop-blur-xl space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                  <Globe className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">Cloud & Backend API Connectivity</h3>
                  <p className="text-xs text-slate-400">Configure the FastAPI backend server URL for Vercel and remote hosting.</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-mono hidden sm:inline">
                  Active: <span className="text-cyan-400 font-semibold">{getApiBaseUrl() || 'Local Proxy (127.0.0.1:8000)'}</span>
                </span>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Backend Server URL
                </label>
                <div className="flex flex-col sm:flex-row gap-2.5">
                  <input
                    type="url"
                    value={customBackendUrl}
                    onChange={(e) => setCustomBackendUrl(e.target.value)}
                    placeholder="https://omnigesture-backend.onrender.com or http://127.0.0.1:8000"
                    className="flex-1 px-4 py-2.5 rounded-xl bg-cyber-bg/70 border border-cyber-border/60 text-white text-sm focus:outline-none focus:border-cyan-500 transition-colors font-mono"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleTestBackend(customBackendUrl)}
                      disabled={testingBackend}
                      className="px-4 py-2.5 rounded-xl bg-cyber-bg hover:bg-slate-800 border border-cyber-border/60 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50"
                    >
                      {testingBackend ? <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" /> : <Activity className="w-3.5 h-3.5 text-cyan-400" />}
                      <span>Test Ping</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveBackendUrl}
                      className="px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs shadow-md shadow-cyan-500/20 transition-all"
                    >
                      Apply
                    </button>
                    {customBackendUrl && (
                      <button
                        type="button"
                        onClick={handleResetBackendUrl}
                        className="p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-400 hover:text-white transition-all"
                        title="Revert to default backend"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Ping Result Banner */}
              {backendTestResult && (
                <div className={`p-3 rounded-xl border flex items-center justify-between text-xs ${
                  backendTestResult.ok
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                }`}>
                  <div className="flex items-center gap-2">
                    {backendTestResult.ok ? <Check className="w-4 h-4 text-emerald-400" /> : <X className="w-4 h-4 text-rose-400" />}
                    <span>
                      {backendTestResult.ok
                        ? `Connected successfully to FastAPI backend! Latency: ${backendTestResult.latency}ms`
                        : `Could not connect: ${backendTestResult.error || 'Connection refused'}`}
                    </span>
                  </div>
                </div>
              )}

              <p className="text-[11px] text-slate-400 leading-relaxed">
                💡 <strong className="text-slate-300">Vercel Deployment Tip:</strong> You can also define <code className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300">VITE_API_URL</code> in your Vercel Project Settings &rarr; Environment Variables to set this automatically for all visitors.
              </p>
            </div>
          </div>

          {/* Section 1: Camera Hardware & Inactivity Auto-Off */}
          <div className="p-6 rounded-2xl bg-cyber-card/80 border border-cyber-border/60 backdrop-blur-xl space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <Camera className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">Camera Hardware & Power Management</h3>
                  <p className="text-xs text-slate-400">Control webcam device index, resolution, and zero-background auto-off.</p>
                </div>
              </div>
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
                liveState.camera_active 
                  ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400' 
                  : 'bg-slate-700/40 border border-slate-600/30 text-slate-400'
              }`}>
                <span className={`w-2 h-2 rounded-full ${liveState.camera_active ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`}></span>
                {liveState.camera_active ? 'Active' : 'Hardware Idle'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Camera Device Index
                </label>
                <select
                  value={settings.camera_index}
                  onChange={(e) => handleChange('camera_index', parseInt(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-xl bg-cyber-bg/70 border border-cyber-border/60 text-white text-sm focus:outline-none focus:border-cyan-500 transition-colors"
                >
                  <option value={0}>Camera 0 (Default Integrated Webcam)</option>
                  <option value={1}>Camera 1 (Secondary / External USB)</option>
                  <option value={2}>Camera 2 (Virtual / OBS Cam)</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1.5">DirectShow (`CAP_DSHOW`) hardware binding.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Stream Resolution
                </label>
                <select
                  value={settings.resolution}
                  onChange={(e) => handleChange('resolution', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-cyber-bg/70 border border-cyber-border/60 text-white text-sm focus:outline-none focus:border-cyan-500 transition-colors"
                >
                  <option value="640x480">640 x 480 (Recommended - Fast 30+ FPS)</option>
                  <option value="1280x720">1280 x 720 (HD 720p)</option>
                  <option value="1920x1080">1920 x 1080 (Full HD 1080p)</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1.5">Higher resolution uses more CPU compute.</p>
              </div>
            </div>

            {/* Zero-Background Auto-off setting */}
            <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-500/20 flex items-start gap-3">
              <ShieldCheck className="w-5 h-5 text-cyan-400 mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-cyan-200">Zero-Background Privacy Guarantee</h4>
                <p className="text-xs text-cyan-300/80 leading-relaxed">
                  When you leave the live feed or close the tab, the backend automatically calls <code className="text-cyan-300 font-mono">cap.release()</code> and powers off your physical webcam. Your webcam light will never stay on in the background.
                </p>
                <div className="pt-2 flex items-center gap-3">
                  {liveState.camera_active ? (
                    <button
                      type="button"
                      onClick={stopCamera}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-300 text-xs font-semibold transition-all"
                    >
                      <EyeOff className="w-3.5 h-3.5" />
                      Force Stop Camera Hardware
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={startCamera}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-semibold transition-all"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Power On Camera Hardware
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Vision & MediaPipe Sensitivity */}
          <div className="p-6 rounded-2xl bg-cyber-card/80 border border-cyber-border/60 backdrop-blur-xl space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">MediaPipe Detection & Landmark Sensitivity</h3>
                <p className="text-xs text-slate-400">Configure Google MediaPipe HandLandmarker confidence and EMA smoothing.</p>
              </div>
            </div>

            <div className="space-y-5">
              {/* Detection Confidence */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Min Hand Detection Confidence
                  </span>
                  <span className="text-xs font-mono font-bold text-cyan-400">
                    {(settings.min_detection_confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.95"
                  step="0.05"
                  value={settings.min_detection_confidence}
                  onChange={(e) => handleChange('min_detection_confidence', parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">Lower values detect hands faster; higher values avoid false positive hand shapes.</p>
              </div>

              {/* Tracking Confidence */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Min Landmark Tracking Confidence
                  </span>
                  <span className="text-xs font-mono font-bold text-blue-400">
                    {(settings.min_tracking_confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.95"
                  step="0.05"
                  value={settings.min_tracking_confidence}
                  onChange={(e) => handleChange('min_tracking_confidence', parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">Controls how aggressively 21 3D joint positions are tracked across consecutive video frames.</p>
              </div>

              {/* EMA Smoothing Alpha */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Landmark EMA Jitter Reduction (Alpha)
                  </span>
                  <span className="text-xs font-mono font-bold text-emerald-400">
                    {settings.smoothing_alpha.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.20"
                  max="0.95"
                  step="0.05"
                  value={settings.smoothing_alpha}
                  onChange={(e) => handleChange('smoothing_alpha', parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">Exponential Moving Average eliminates hand jitter and micro-tremors.</p>
              </div>
            </div>
          </div>

          {/* Section 3: Machine Learning & Recognition Behavior */}
          <div className="p-6 rounded-2xl bg-cyber-card/80 border border-cyber-border/60 backdrop-blur-xl space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Machine Learning Inference Mode</h3>
                <p className="text-xs text-slate-400">Choose between trained Scikit-learn model with geometric fallback or pure geometry.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div 
                onClick={() => handleChange('inference_mode', 'hybrid')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  settings.inference_mode === 'hybrid'
                    ? 'bg-purple-500/15 border-purple-500/50 shadow-lg shadow-purple-500/10'
                    : 'bg-cyber-bg/50 border-cyber-border/40 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm text-white">Hybrid ML + Fallback</span>
                  {settings.inference_mode === 'hybrid' && <CheckCircle2 className="w-4 h-4 text-purple-400" />}
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Uses the active <strong className="text-purple-300 font-normal">best_model.pkl</strong> (82 scale-invariant features). Falls back to geometric heuristics if confidence drops below threshold.
                </p>
              </div>

              <div 
                onClick={() => handleChange('inference_mode', 'rule_only')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  settings.inference_mode === 'rule_only'
                    ? 'bg-blue-500/15 border-blue-500/50 shadow-lg shadow-blue-500/10'
                    : 'bg-cyber-bg/50 border-cyber-border/40 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm text-white">Pure Geometric Rules</span>
                  {settings.inference_mode === 'rule_only' && <CheckCircle2 className="w-4 h-4 text-blue-400" />}
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Bypasses machine learning classifier and evaluates finger curl angles, MCP heights, and tip distances directly.
                </p>
              </div>
            </div>

            {/* Recognition Threshold */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Classification Confidence Threshold
                </span>
                <span className="text-xs font-mono font-bold text-purple-400">
                  {(settings.recognition_threshold * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min="0.30"
                max="0.95"
                step="0.05"
                value={settings.recognition_threshold}
                onChange={(e) => handleChange('recognition_threshold', parseFloat(e.target.value))}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
              />
              <p className="text-[11px] text-slate-500 mt-1">Predictions with probability below this value will not trigger recognition.</p>
            </div>
          </div>
        </div>

        {/* Right 1 Column: Diagnostics & Quick Reference */}
        <div className="space-y-6">
          {/* Active Model Status Card */}
          <div className="p-6 rounded-2xl bg-cyber-card/80 border border-cyber-border/60 backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Current Model Engine</span>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Deployed
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-xs text-slate-400">Active Model</p>
                <p className="text-base font-bold text-white font-mono">{modelInfo.model_name || 'best_model.pkl'}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="p-2.5 rounded-xl bg-cyber-bg/60 border border-cyber-border/40">
                  <p className="text-[11px] text-slate-400">Accuracy</p>
                  <p className="text-sm font-bold text-cyan-400">{modelInfo.accuracy ? `${(modelInfo.accuracy * 100).toFixed(1)}%` : '99.5%'}</p>
                </div>
                <div className="p-2.5 rounded-xl bg-cyber-bg/60 border border-cyber-border/40">
                  <p className="text-[11px] text-slate-400">Supported Classes</p>
                  <p className="text-sm font-bold text-purple-400">{modelInfo.classes_count || 17} Gestures</p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleHotReloadModel}
                disabled={reloadingModel}
                className="w-full mt-2 flex items-center justify-center gap-2 py-2 px-3 rounded-xl border border-purple-500/40 bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 text-xs font-semibold transition-all disabled:opacity-50"
              >
                <Layers className="w-3.5 h-3.5" />
                {reloadingModel ? 'Reloading Model...' : 'Hot-Reload Model from Disk'}
              </button>
            </div>
          </div>

          {/* System Runtime Diagnostics */}
          <div className="p-6 rounded-2xl bg-cyber-card/80 border border-cyber-border/60 backdrop-blur-xl space-y-4">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <Server className="w-4 h-4 text-cyan-400" />
              Runtime Stack Diagnostics
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between py-1.5 border-b border-cyber-border/30">
                <span className="text-slate-400">Vision Backend</span>
                <span className="font-mono text-cyan-300">MediaPipe Tasks 0.10+</span>
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-cyber-border/30">
                <span className="text-slate-400">Feature Vector</span>
                <span className="font-mono text-purple-300">82-dim Normalized</span>
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-cyber-border/30">
                <span className="text-slate-400">Hardware Backend</span>
                <span className="font-mono text-emerald-300">OpenCV DirectShow</span>
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-cyber-border/30">
                <span className="text-slate-400">Database Engine</span>
                <span className="font-mono text-slate-300">SQLite 3 (`gesture.db`)</span>
              </div>
              <div className="flex items-center justify-between py-1.5">
                <span className="text-slate-400">API Gateway</span>
                <span className="font-mono text-amber-300">FastAPI + Uvicorn</span>
              </div>
            </div>
          </div>

          {/* Keyboard Shortcuts Card */}
          <div className="p-6 rounded-2xl bg-cyber-card/80 border border-cyber-border/60 backdrop-blur-xl space-y-4">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <Command className="w-4 h-4 text-amber-400" />
              Keyboard Quick Shortcuts
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-400">Start / Pause Stream</span>
                <kbd className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono font-bold">Space</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-400">Capture Screenshot</span>
                <kbd className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono font-bold">S</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-400">Collect Data Sample</span>
                <kbd className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono font-bold">C</kbd>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-400">Toggle Fullscreen HUD</span>
                <kbd className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono font-bold">F</kbd>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
