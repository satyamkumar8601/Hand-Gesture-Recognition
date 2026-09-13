import React, { useState, useEffect, useRef } from 'react';
import { CameraFeed } from '../components/CameraFeed';
import { GestureCard } from '../components/GestureCard';
import { useApp } from '../context/AppContext';
import { apiUrl } from '../config/api';
import {
  Sparkles,
  LayoutDashboard,
  Paintbrush,
  MousePointer,
  Activity,
  RotateCcw,
  Trash2,
  Monitor,
  ShieldCheck,
  CheckCircle2,
  Layers,
  HelpCircle,
  Volume2,
  VolumeX,
  Plus,
  Delete,
  Download,
  RefreshCw,
  MessageSquare,
} from 'lucide-react';

const PALETTE_COLORS = [
  { name: 'Cyan', bg: 'bg-[#00e5ff]', border: 'border-[#00e5ff]' },
  { name: 'Neon Pink', bg: 'bg-[#ff007f]', border: 'border-[#ff007f]' },
  { name: 'Emerald', bg: 'bg-[#00ff88]', border: 'border-[#00ff88]' },
  { name: 'Gold', bg: 'bg-[#ffd700]', border: 'border-[#ffd700]' },
  { name: 'Purple', bg: 'bg-[#b026ff]', border: 'border-[#b026ff]' },
  { name: 'Eraser', bg: 'bg-slate-700', border: 'border-slate-500' },
];

export const LiveRecognition = () => {
  const {
    liveState,
    setStudioMode,
    clearCanvas,
    undoCanvas,
    setCanvasColor,
    toggleWhiteboard,
    setBrushSize,
    toggleVirtualMouse,
    voiceEnabled,
    setVoiceEnabled,
    sentenceWords,
    speakGesture,
    speakText,
    addGestureToSentence,
    speakSentence,
    removeLastWord,
    clearSentence,
    addNotification,
  } = useApp();

  const [showGuide, setShowGuide] = useState(false);
  const [brushVal, setBrushVal] = useState(5);
  const [rehabReps, setRehabReps] = useState(0);
  const [savingArtwork, setSavingArtwork] = useState(false);
  const rehabCycleRef = useRef({ wasClosed: false });

  const activeMode = liveState.mode || 1;

  // Rehab Exercise Repetition Counter: Tracks Fist (closed >= 60%) to Palm (open <= 35%) cycles
  useEffect(() => {
    if (activeMode === 4 && liveState.hand_detected) {
      const grip = liveState.rehab_grip_closure || 0;
      if (grip >= 60) {
        rehabCycleRef.current.wasClosed = true;
      } else if (grip <= 35 && rehabCycleRef.current.wasClosed) {
        rehabCycleRef.current.wasClosed = false;
        setRehabReps(prev => {
          const nextRep = prev + 1;
          if (voiceEnabled) {
            speakText(`Rep ${nextRep}`);
          }
          return nextRep;
        });
      }
    }
  }, [activeMode, liveState.hand_detected, liveState.rehab_grip_closure, voiceEnabled, speakText]);

  // Top 4 probability classes
  const sortedProbabilities = Object.entries(liveState.probabilities || {})
    .sort(([, a], [, b]) => b - a)
    .slice(0, 4);

  const handleBrushChange = (e) => {
    const val = parseInt(e.target.value, 10);
    setBrushVal(val);
    setBrushSize(val);
  };

  const handleSaveArtwork = async () => {
    setSavingArtwork(true);
    try {
      const res = await fetch(apiUrl('/api/screenshot'), { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        addNotification(`Artwork saved: ${data.filename}`, 'success');
      } else {
        addNotification(data.error || 'Failed to export artwork', 'error');
      }
    } catch (e) {
      addNotification('Error saving artwork', 'error');
    } finally {
      setSavingArtwork(false);
    }
  };

  return (
    <div className="space-y-6 w-full animate-in fade-in duration-300">
      {/* Studio Mode Switcher Tabs */}
      <div className="glass-card rounded-2xl p-2 sm:p-2.5 border border-light-border dark:border-dark-border shadow-lg">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <button
            onClick={() => setStudioMode(1)}
            className={`flex items-center justify-center gap-2 py-3 px-3 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 ${
              activeMode === 1
                ? 'bg-primary text-white shadow-glow-primary scale-[1.02]'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            }`}
          >
            <LayoutDashboard className="h-4 w-4 flex-shrink-0" />
            <span className="truncate">HUD Analytics</span>
          </button>

          <button
            onClick={() => setStudioMode(2)}
            className={`flex items-center justify-center gap-2 py-3 px-3 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 ${
              activeMode === 2
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/25 scale-[1.02]'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            }`}
          >
            <Paintbrush className="h-4 w-4 flex-shrink-0 text-cyan-300" />
            <span className="truncate">Air Canvas</span>
          </button>

          <button
            onClick={() => setStudioMode(3)}
            className={`flex items-center justify-center gap-2 py-3 px-3 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 ${
              activeMode === 3
                ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25 scale-[1.02]'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            }`}
          >
            <MousePointer className="h-4 w-4 flex-shrink-0 text-emerald-300" />
            <span className="truncate">Virtual Mouse</span>
          </button>

          <button
            onClick={() => setStudioMode(4)}
            className={`flex items-center justify-center gap-2 py-3 px-3 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 ${
              activeMode === 4
                ? 'bg-gradient-to-r from-pink-500 to-rose-600 text-white shadow-lg shadow-pink-500/25 scale-[1.02]'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            }`}
          >
            <Activity className="h-4 w-4 flex-shrink-0 text-pink-300" />
            <span className="truncate">Biometrics & Rehab</span>
          </button>
        </div>
      </div>

      {/* Sign-to-Speech & Real-time Sentence Builder Bar */}
      <div className="glass-card rounded-2xl p-4 border border-light-border dark:border-dark-border shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-3 bg-gradient-to-r from-slate-900/40 via-purple-950/20 to-slate-900/40">
        <div className="flex flex-wrap items-center gap-2.5 flex-1">
          <button
            onClick={() => {
              const nextState = !voiceEnabled;
              setVoiceEnabled(nextState);
              if (nextState) {
                speakText('Voice narration activated');
                addNotification('Voice Narration Activated', 'success');
              } else {
                addNotification('Voice Narration Muted', 'info');
              }
            }}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shadow-sm ${
              voiceEnabled
                ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-purple-500/25 animate-pulse'
                : 'bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
            title="Toggle real-time voice speech synthesis for recognized gestures"
          >
            {voiceEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4 text-slate-400" />}
            <span>{voiceEnabled ? 'Voice: ON' : 'Voice: OFF'}</span>
          </button>

          <div className="h-5 w-[1px] bg-slate-300 dark:bg-slate-700 hidden sm:block" />

          {/* Sentence Builder Chips */}
          <div className="flex items-center gap-1.5 flex-wrap min-h-[36px] flex-1">
            <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
              <MessageSquare className="h-3 w-3 text-purple-400" /> Phrase:
            </span>
            {sentenceWords.length === 0 ? (
              <span className="text-xs text-slate-500 italic">
                Show gestures and click "+ Add" to build phrases with voice synthesis...
              </span>
            ) : (
              sentenceWords.map((word, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30 shadow-sm animate-in fade-in"
                >
                  {word}
                </span>
              ))
            )}
          </div>
        </div>

        {/* Sentence Action Buttons */}
        <div className="flex items-center gap-1.5 self-end md:self-auto flex-shrink-0">
          <button
            onClick={() => {
              if (liveState.primary_gesture && liveState.primary_gesture !== 'No Hand') {
                addGestureToSentence(liveState.primary_gesture);
              }
            }}
            disabled={!liveState.hand_detected || liveState.primary_gesture === 'No Hand'}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary/15 hover:bg-primary/25 text-primary border border-primary/30 text-xs font-semibold transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="Add current gesture to sentence phrase"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Gesture</span>
          </button>

          <button
            onClick={speakSentence}
            disabled={sentenceWords.length === 0}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/30 text-xs font-bold transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="Speak the full constructed sentence"
          >
            <Volume2 className="h-3.5 w-3.5" />
            <span>Speak</span>
          </button>

          <button
            onClick={removeLastWord}
            disabled={sentenceWords.length === 0}
            className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-200 text-xs border border-light-border dark:border-dark-border disabled:opacity-30 disabled:cursor-not-allowed"
            title="Backspace: Remove last gesture word"
          >
            <Delete className="h-3.5 w-3.5" />
          </button>

          <button
            onClick={clearSentence}
            disabled={sentenceWords.length === 0}
            className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs border border-rose-500/30 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Clear all phrase words"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Main Two-Column Responsive Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Live Camera Video Stream */}
        <div className="lg:col-span-7 space-y-4">
          <CameraFeed />

          {/* Quick Tip Pill */}
          <div className="flex items-center justify-between px-4 py-2.5 rounded-xl bg-slate-100/80 dark:bg-slate-800/50 border border-light-border dark:border-dark-border text-xs text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-accent" />
              <span>
                {activeMode === 1 && '3D MediaPipe tracking 21 joints with scale-invariant ML gesture classification.'}
                {activeMode === 2 && 'Point with index finger to paint. Hover with Peace sign (✌️) to pause drawing.'}
                {activeMode === 3 && 'Move index fingertip to steer cursor. Pinch thumb & index (👌) to click.'}
                {activeMode === 4 && 'Track grip closure percentage and finger flexion angles in real-time.'}
              </span>
            </span>
            <button
              onClick={() => setShowGuide(prev => !prev)}
              className="text-primary hover:underline font-semibold flex items-center gap-1 flex-shrink-0 ml-2"
            >
              <HelpCircle className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{showGuide ? 'Hide Guide' : 'Instructions'}</span>
            </button>
          </div>

          {/* Collapsible Usage Guide */}
          {showGuide && (
            <div className="glass-card rounded-2xl p-5 border border-primary/30 space-y-3 animate-in fade-in text-xs">
              <h4 className="font-bold uppercase tracking-wider text-primary">
                Active Mode Gesture Guide: {liveState.mode_name}
              </h4>
              {activeMode === 1 && (
                <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                  Hold your hand upright in front of the camera. The system recognizes 17 gestures (Open Palm, Fist, Thumbs Up/Down, Victory, OK Sign, Rock Sign, Peace, etc.) with real-time probability distributions.
                </p>
              )}
              {activeMode === 2 && (
                <ul className="list-disc pl-4 space-y-1 text-slate-600 dark:text-slate-300">
                  <li><strong>Draw:</strong> Extend only your index finger ☝️ and move it in the air.</li>
                  <li><strong>Selection / Hover:</strong> Extend both index and middle fingers ✌️ to stop drawing.</li>
                  <li><strong>Change Color:</strong> Click color chips on the right or tap the top palette bar.</li>
                  <li><strong>Whiteboard:</strong> Toggle Whiteboard mode to sketch on a clean dark canvas.</li>
                </ul>
              )}
              {activeMode === 3 && (
                <ul className="list-disc pl-4 space-y-1 text-slate-600 dark:text-slate-300">
                  <li><strong>Steer:</strong> Move your hand within the inner bounding box.</li>
                  <li><strong>Left Click:</strong> Pinch thumb tip and index fingertip together.</li>
                  <li><strong>Click & Drag:</strong> Hold pinch while moving hand.</li>
                  <li><strong>Safety:</strong> Move cursor to any screen corner to trigger PyAutoGUI failsafe.</li>
                </ul>
              )}
              {activeMode === 4 && (
                <ul className="list-disc pl-4 space-y-1 text-slate-600 dark:text-slate-300">
                  <li><strong>Grip Closure:</strong> Opens from 0% (wide open palm) to 100% (tight fist).</li>
                  <li><strong>Range of Motion:</strong> Detects individual finger extensions and symmetry across both hands.</li>
                </ul>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Dynamic Interactive Controls According to Mode */}
        <div className="lg:col-span-5 space-y-6">
          {/* ============================================================== */}
          {/* MODE 2: AIR CANVAS DEDICATED CONTROLS */}
          {/* ============================================================== */}
          {activeMode === 2 && (
            <div className="glass-card rounded-2xl p-5 sm:p-6 border border-cyan-500/30 space-y-5 shadow-lg shadow-cyan-500/5">
              <div className="flex items-center justify-between border-b border-light-border dark:border-dark-border pb-3">
                <div className="flex items-center gap-2.5">
                  <Paintbrush className="h-5 w-5 text-cyan-400" />
                  <div>
                    <h3 className="font-bold text-sm sm:text-base text-slate-800 dark:text-white">Air Canvas Palette</h3>
                    <p className="text-[11px] text-slate-400">Virtual Finger Painting Studio</p>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
                  Active: {liveState.canvas_color || 'Cyan'}
                </span>
              </div>

              {/* Color Chips */}
              <div>
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-2.5">
                  Select Drawing Color:
                </label>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                  {PALETTE_COLORS.map(col => {
                    const isSelected = (liveState.canvas_color || 'Cyan') === col.name;
                    return (
                      <button
                        key={col.name}
                        onClick={() => setCanvasColor(col.name)}
                        className={`flex flex-col items-center gap-1.5 p-2 rounded-xl border transition-all ${
                          isSelected
                            ? 'border-primary bg-primary/10 shadow-glow-primary scale-105 font-bold'
                            : 'border-light-border dark:border-dark-border hover:bg-slate-100 dark:hover:bg-slate-800/60'
                        }`}
                      >
                        <span className={`h-6 w-6 rounded-full ${col.bg} border ${col.border} shadow-sm`} />
                        <span className="text-[10px] truncate max-w-full">{col.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Brush Thickness Slider */}
              <div>
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="font-semibold text-slate-600 dark:text-slate-300">Brush Thickness</span>
                  <span className="font-mono text-cyan-400 font-bold">{brushVal} px</span>
                </div>
                <input
                  type="range"
                  min="2"
                  max="30"
                  value={brushVal}
                  onChange={handleBrushChange}
                  className="w-full accent-cyan-400 cursor-pointer"
                />
              </div>

              {/* Action Buttons: Undo, Clear, Whiteboard */}
              <div className="grid grid-cols-3 gap-2.5 pt-2 border-t border-light-border dark:border-dark-border">
                <button
                  onClick={undoCanvas}
                  className="flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 border border-light-border dark:border-dark-border transition-colors"
                >
                  <RotateCcw className="h-3.5 w-3.5 text-primary" />
                  <span>Undo</span>
                </button>

                <button
                  onClick={clearCanvas}
                  className="flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border border-rose-500/30 text-xs font-semibold transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Clear</span>
                </button>

                <button
                  onClick={toggleWhiteboard}
                  className={`flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl text-xs font-semibold border transition-colors ${
                    liveState.whiteboard_mode
                      ? 'bg-primary text-white border-primary shadow-glow-primary'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-light-border dark:border-dark-border'
                  }`}
                >
                  <Monitor className="h-3.5 w-3.5" />
                  <span className="truncate">{liveState.whiteboard_mode ? 'Camera' : 'Board'}</span>
                </button>

                <button
                  onClick={handleSaveArtwork}
                  disabled={savingArtwork}
                  className="col-span-3 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-400 border border-cyan-500/30 text-xs font-bold transition-colors shadow-sm"
                  title="Download and save your drawing artwork as PNG"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>{savingArtwork ? 'Saving Artwork...' : 'Export Artwork (PNG)'}</span>
                </button>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* MODE 3: VIRTUAL MOUSE DEDICATED CONTROLS */}
          {/* ============================================================== */}
          {activeMode === 3 && (
            <div className="glass-card rounded-2xl p-5 sm:p-6 border border-emerald-500/30 space-y-5 shadow-lg shadow-emerald-500/5">
              <div className="flex items-center justify-between border-b border-light-border dark:border-dark-border pb-3">
                <div className="flex items-center gap-2.5">
                  <MousePointer className="h-5 w-5 text-emerald-400" />
                  <div>
                    <h3 className="font-bold text-sm sm:text-base text-slate-800 dark:text-white">Virtual Mouse Control</h3>
                    <p className="text-[11px] text-slate-400">Hand-to-Cursor Mapping</p>
                  </div>
                </div>
                <span
                  className={`px-2.5 py-1 rounded-full text-[11px] font-bold border ${
                    liveState.mouse_enabled
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 animate-pulse'
                      : 'bg-slate-500/15 text-slate-400 border-slate-500/30'
                  }`}
                >
                  {liveState.mouse_enabled ? '● ACTIVE' : '○ PAUSED'}
                </span>
              </div>

              {/* Big Toggle Switch Button */}
              <button
                onClick={toggleVirtualMouse}
                className={`w-full py-3.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2.5 shadow-lg transition-all transform active:scale-95 ${
                  liveState.mouse_enabled
                    ? 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-emerald-500/25'
                    : 'bg-slate-700 hover:bg-slate-600 text-slate-200'
                }`}
              >
                <MousePointer className="h-4 w-4" />
                <span>{liveState.mouse_enabled ? 'Pause Mouse Controller' : 'Activate Mouse Controller'}</span>
              </button>

              <div className="p-3.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-light-border dark:border-dark-border text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Pinch Ratio</span>
                  <span className="font-mono text-emerald-400 font-bold">
                    {liveState.probabilities ? `${Math.round(liveState.confidence)}%` : '0%'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Smoothing Factor</span>
                  <span className="font-mono text-slate-300 font-bold">0.75 (Snappy)</span>
                </div>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* MODE 4: BIOMETRICS & REHAB DEDICATED CONTROLS */}
          {/* ============================================================== */}
          {activeMode === 4 && (
            <div className="glass-card rounded-2xl p-5 sm:p-6 border border-pink-500/30 space-y-5 shadow-lg shadow-pink-500/5">
              <div className="flex items-center justify-between border-b border-light-border dark:border-dark-border pb-3">
                <div className="flex items-center gap-2.5">
                  <Activity className="h-5 w-5 text-pink-400" />
                  <div>
                    <h3 className="font-bold text-sm sm:text-base text-slate-800 dark:text-white">Rehab & Biometrics</h3>
                    <p className="text-[11px] text-slate-400">Clinical ROM & Grip Closure Gauge</p>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-pink-500/15 text-pink-400 border border-pink-500/30">
                  Live Stream
                </span>
              </div>

              {/* Exercise Repetition Counter */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-pink-950/30 to-slate-900 border border-pink-500/30">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-pink-400" />
                    <span className="text-xs font-bold text-slate-200">Rehab Repetition Counter</span>
                  </div>
                  <button
                    onClick={() => setRehabReps(0)}
                    className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors text-[10px] flex items-center gap-1 px-2"
                    title="Reset repetition count"
                  >
                    <RefreshCw className="h-3 w-3" /> Reset
                  </button>
                </div>
                <div className="flex items-baseline justify-between mt-3">
                  <div>
                    <span className="text-4xl font-black text-white font-mono">{rehabReps}</span>
                    <span className="text-xs text-pink-400 font-bold ml-1.5 uppercase">Completed Reps</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                      (liveState.rehab_grip_closure || 0) >= 60
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                        : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    }`}>
                      {(liveState.rehab_grip_closure || 0) >= 60 ? '✊ Fist Clenched' : '✋ Open Hand'}
                    </span>
                  </div>
                </div>
                <p className="text-[11px] text-slate-400 mt-2 italic">
                  Exercise: Squeeze into a tight fist (&ge;60%), then open hand fully (&le;35%) to count a rep.
                </p>
              </div>

              {/* Grip Closure Gauge */}
              <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-light-border dark:border-dark-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">Hand Grip Closure</span>
                  <span className="font-mono text-sm font-extrabold text-pink-400">
                    {liveState.rehab_grip_closure || 0}%
                  </span>
                </div>
                <div className="h-3 w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-pink-500 to-rose-500 rounded-full transition-all duration-200"
                    style={{ width: `${Math.min(100, liveState.rehab_grip_closure || 0)}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
                  <span>0% (Open Palm)</span>
                  <span>50%</span>
                  <span>100% (Tight Fist)</span>
                </div>
              </div>

              {/* Finger-by-Finger ROM Status */}
              <div>
                <span className="text-[11px] font-bold text-slate-400 block mb-2 uppercase tracking-wider">
                  Individual Joint Flexion States:
                </span>
                <div className="grid grid-cols-5 gap-1.5 text-center">
                  {[
                    { key: 'thumb', label: 'Thumb' },
                    { key: 'index', label: 'Index' },
                    { key: 'middle', label: 'Middle' },
                    { key: 'ring', label: 'Ring' },
                    { key: 'pinky', label: 'Pinky' },
                  ].map(f => {
                    const isExt = liveState.finger_states && liveState.finger_states[f.key];
                    return (
                      <div
                        key={f.key}
                        className={`p-2 rounded-xl border text-[10px] font-bold transition-colors ${
                          isExt
                            ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                            : 'bg-slate-800/60 border-slate-700 text-slate-400'
                        }`}
                      >
                        <div className="truncate">{f.label}</div>
                        <div className="mt-1 font-mono">{isExt ? 'OPEN' : 'CURL'}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Extended Fingers Counter */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-light-border dark:border-dark-border text-center">
                  <p className="text-[11px] text-slate-400 font-semibold mb-1">Extended Fingers</p>
                  <p className="text-2xl font-extrabold text-white font-mono">
                    {liveState.rehab_extended_fingers || 0} <span className="text-xs text-slate-400">/ 10</span>
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-light-border dark:border-dark-border text-center">
                  <p className="text-[11px] text-slate-400 font-semibold mb-1">Active Hands</p>
                  <p className="text-2xl font-extrabold text-cyan-400 font-mono">
                    {liveState.hands_count || 0}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Common Gesture Card Component */}
          <GestureCard />

          {/* Model Class Probability Distribution Card */}
          {sortedProbabilities.length > 0 && (
            <div className="glass-card rounded-2xl p-5 border border-light-border dark:border-dark-border shadow-lg">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center justify-between">
                <span>Top Candidate Probabilities</span>
                <ShieldCheck className="h-3.5 w-3.5 text-accent" />
              </h4>

              <div className="space-y-3">
                {sortedProbabilities.map(([gesture, prob]) => {
                  const pct = Math.round(prob * 100);
                  return (
                    <div key={gesture}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-semibold text-slate-700 dark:text-slate-300">{gesture}</span>
                        <span className="font-mono text-slate-500 dark:text-slate-400">{pct}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary to-accent rounded-full transition-all duration-300"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

