import React from 'react';
import {
  LayoutDashboard,
  Video,
  Database,
  Cpu,
  BarChart3,
  History,
  Settings,
  Hand,
  Sparkles,
  Zap,
  X,
  Paintbrush,
  MousePointer,
  Activity,
} from 'lucide-react';
import { useApp } from '../context/AppContext';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'live', label: 'Live Recognition', icon: Video, badge: 'LIVE' },
  { id: 'dataset', label: 'Dataset Studio', icon: Database },
  { id: 'train', label: 'Train Models', icon: Cpu, badge: 'ML' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'history', label: 'History Logs', icon: History },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export const Sidebar = () => {
  const { activePage, setActivePage, modelInfo, liveState, isMobileMenuOpen, closeMobileMenu, setStudioMode, startCamera } = useApp();

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300"
          onClick={closeMobileMenu}
          aria-hidden="true"
        />
      )}

      {/* Sidebar (Responsive: Slide-out Drawer on Mobile/Tablet, Static on Desktop) */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 flex flex-col justify-between border-r border-light-border dark:border-dark-border bg-light-card/95 dark:bg-dark-card/95 backdrop-blur-2xl transition-transform duration-300 ease-in-out lg:static lg:w-64 lg:translate-x-0 ${
          isMobileMenuOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div>
          {/* Brand Header */}
          <div className="h-20 flex items-center justify-between px-6 border-b border-light-border dark:border-dark-border/60">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-primary to-secondary flex items-center justify-center shadow-glow-primary text-white flex-shrink-0">
                <Hand className="h-5 w-5 animate-pulse" />
              </div>
              <div>
                <h1 className="font-extrabold text-lg tracking-wider bg-gradient-to-r from-primary via-secondary to-cyber-cyan bg-clip-text text-transparent brand-font">
                  OMNIGESTURE
                </h1>
                <p className="text-[10px] font-semibold tracking-widest text-slate-400 uppercase flex items-center gap-1">
                  <Sparkles className="h-2.5 w-2.5 text-cyber-cyan" />
                  AI Studio // v2.0
                </p>
              </div>
            </div>

            {/* Mobile Close Button */}
            <button
              onClick={closeMobileMenu}
              className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
              aria-label="Close navigation"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5 overflow-y-auto max-h-[calc(100vh-14rem)]">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActivePage(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 group ${
                    isActive
                      ? 'bg-primary text-white shadow-glow-primary font-semibold'
                      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon
                      className={`h-4 w-4 transition-transform duration-200 group-hover:scale-110 ${
                        isActive ? 'text-white' : 'text-slate-400 dark:text-slate-400 group-hover:text-primary'
                      }`}
                    />
                    <span>{item.label}</span>
                  </div>

                  {item.badge && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-md font-bold ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : item.badge === 'LIVE'
                          ? 'bg-accent/15 text-accent border border-accent/30 animate-pulse'
                          : 'bg-secondary/15 text-secondary border border-secondary/30'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Interactive Studio Modes */}
          <div className="px-4 pt-1 pb-2">
            <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Sparkles className="h-2.5 w-2.5 text-accent" />
              Studio Modes
            </p>
            <div className="space-y-1">
              {[
                { mode: 1, label: 'HUD Analytics', icon: LayoutDashboard, color: 'text-primary' },
                { mode: 2, label: 'Air Canvas', icon: Paintbrush, color: 'text-cyan-400' },
                { mode: 3, label: 'Virtual Mouse', icon: MousePointer, color: 'text-emerald-400' },
                { mode: 4, label: 'Biometrics & Rehab', icon: Activity, color: 'text-pink-400' },
              ].map(m => {
                const isSelected = activePage === 'live' && liveState.mode === m.mode;
                const ModeIcon = m.icon;
                return (
                  <button
                    key={m.mode}
                    onClick={() => {
                      setStudioMode(m.mode);
                      startCamera();
                      setActivePage('live');
                      closeMobileMenu();
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                      isSelected
                        ? 'bg-gradient-to-r from-primary/20 to-accent/20 border border-accent/40 text-white font-bold shadow-sm'
                        : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/50 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <ModeIcon className={`h-3.5 w-3.5 ${m.color}`} />
                      <span>{m.label}</span>
                    </div>
                    {isSelected && (
                      <span className="h-1.5 w-1.5 rounded-full bg-accent animate-ping" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Model & System Status Widget at bottom */}
        <div className="p-4 m-3 rounded-2xl bg-gradient-to-br from-slate-100 to-slate-200/50 dark:from-slate-800/70 dark:to-slate-900/90 border border-light-border dark:border-dark-border/80 flex-shrink-0">
          <div className="flex items-center justify-between text-xs font-semibold mb-2">
            <span className="text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <Zap className="h-3 w-3 text-accent" /> Active Engine
            </span>
            <span className="text-accent font-bold">
              {modelInfo.accuracy ? `${modelInfo.accuracy}%` : '98.4%'}
            </span>
          </div>
          <p className="text-sm font-bold text-slate-800 dark:text-white truncate">
            {modelInfo.model_name || 'Random Forest'}
          </p>
          <div className="mt-2 pt-2 border-t border-slate-200 dark:border-slate-700/60 flex items-center justify-between text-[11px] text-slate-500">
            <span>Studio Mode:</span>
            <span className="text-primary font-semibold truncate max-w-[110px]">
              {liveState.mode_name || 'HUD Analytics'}
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
            <span>Webcam:</span>
            <span className={liveState.camera_active ? 'text-accent font-semibold' : 'text-slate-400'}>
              {liveState.camera_active ? '● ONLINE' : '○ STANDBY'}
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};
