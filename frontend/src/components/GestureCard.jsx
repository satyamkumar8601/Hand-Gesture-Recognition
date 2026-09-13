import React from 'react';
import { Check, X, Zap, Cpu, Sparkles } from 'lucide-react';
import { useApp } from '../context/AppContext';

export const GestureCard = () => {
  const { liveState } = useApp();

  const fingerOrder = [
    { key: 'thumb', label: 'Thumb' },
    { key: 'index', label: 'Index' },
    { key: 'middle', label: 'Middle' },
    { key: 'ring', label: 'Ring' },
    { key: 'pinky', label: 'Pinky' },
  ];

  const gestureName = liveState.primary_gesture || 'No Hand';
  const confidence = liveState.confidence || 0;
  const isMl = liveState.is_ml;
  const icon = liveState.icon || '✋';

  return (
    <div className="glass-card rounded-2xl p-6 border border-light-border dark:border-dark-border flex flex-col justify-between">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Current Gesture
          </span>
          <span
            className={`text-[11px] px-2.5 py-1 rounded-full font-bold flex items-center gap-1.5 border ${
              isMl
                ? 'bg-cyber-cyan/15 border-cyber-cyan/40 text-cyber-cyan shadow-glow-cyan'
                : 'bg-cyber-gold/15 border-cyber-gold/40 text-cyber-gold'
            }`}
          >
            {isMl ? <Cpu className="h-3 w-3" /> : <Sparkles className="h-3 w-3" />}
            {isMl ? 'ML CLASSIFIER' : 'RULE HYBRID'}
          </span>
        </div>

        {/* Big Animated Gesture Display */}
        <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-100/80 to-slate-200/50 dark:from-slate-800/60 dark:to-slate-900/80 border border-light-border dark:border-dark-border/80 flex items-center justify-center gap-6">
          <span className="text-6xl filter drop-shadow-md select-none transform hover:scale-110 transition-transform duration-200">
            {icon}
          </span>
          <div>
            <h3 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white brand-font">
              {gestureName}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {liveState.hand_detected ? 'Spatial 3D Pattern Matched' : 'Awaiting hand in camera view...'}
            </p>
          </div>
        </div>

        {/* Animated Confidence Bar */}
        <div className="mt-5">
          <div className="flex items-center justify-between text-xs font-semibold mb-1.5">
            <span className="text-slate-600 dark:text-slate-400">Confidence Score</span>
            <span className="text-accent font-mono font-bold text-sm">{confidence}%</span>
          </div>
          <div className="h-3 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-300 dark:border-slate-700">
            <div
              className="h-full bg-gradient-to-r from-primary via-secondary to-accent rounded-full transition-all duration-300 shadow-glow-accent"
              style={{ width: `${Math.min(100, Math.max(0, confidence))}%` }}
            />
          </div>
        </div>
      </div>

      {/* Finger States Detection Grid */}
      <div className="mt-6 pt-5 border-t border-slate-200 dark:border-slate-800">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
          <Zap className="h-3.5 w-3.5 text-accent" />
          Individual Finger States
        </h4>

        <div className="grid grid-cols-5 gap-2">
          {fingerOrder.map((f) => {
            const isOpen = liveState.finger_states?.[f.key];
            return (
              <div
                key={f.key}
                className={`py-2 px-1 rounded-xl border flex flex-col items-center justify-center transition-all duration-200 ${
                  isOpen
                    ? 'bg-accent/15 border-accent/40 text-accent font-bold shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800/50 border-slate-300 dark:border-slate-700/60 text-slate-400'
                }`}
              >
                <div className="mb-0.5">
                  {isOpen ? <Check className="h-4 w-4" /> : <X className="h-4 w-4 opacity-50" />}
                </div>
                <span className="text-[11px] font-medium tracking-tight">{f.label}</span>
                <span className="text-[9px] uppercase font-bold tracking-wider opacity-80">
                  {isOpen ? 'Open' : 'Curl'}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
