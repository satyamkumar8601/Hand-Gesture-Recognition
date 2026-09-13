import React from 'react';
import {
  Sun,
  Moon,
  Camera,
  Activity,
  CameraOff,
  Menu,
  Server,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiUrl } from '../config/api';

export const Navbar = () => {
  const {
    activePage,
    setActivePage,
    theme,
    toggleTheme,
    liveState,
    backendStatus,
    startCamera,
    stopCamera,
    addNotification,
    toggleMobileMenu,
  } = useApp();

  const getPageTitle = () => {
    switch (activePage) {
      case 'dashboard':
        return { title: 'Executive Dashboard', subtitle: 'Real-time gesture analytics & system health' };
      case 'live':
        return { title: 'Live Gesture Recognition', subtitle: 'Ultra-low latency 3D landmark tracking & classification' };
      case 'dataset':
        return { title: 'Dataset Studio', subtitle: 'Capture, organize, and manage gesture landmark training data' };
      case 'train':
        return { title: 'Model Training & Evaluation', subtitle: 'Train, benchmark, and deploy 4 machine learning classifiers' };
      case 'analytics':
        return { title: 'Performance Analytics', subtitle: 'Statistical trends, gesture distributions, and accuracy charts' };
      case 'history':
        return { title: 'Recognition History', subtitle: 'Historical database log with search, filter, and export' };
      case 'settings':
        return { title: 'System Settings', subtitle: 'Camera parameters, detection confidence, and hotkeys' };
      default:
        return { title: 'OmniGesture Studio', subtitle: 'AI-Powered Computer Vision System' };
    }
  };

  const { title, subtitle } = getPageTitle();

  const handleScreenshot = async () => {
    try {
      const res = await fetch(apiUrl('/api/screenshot'), { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        addNotification(`Screenshot captured: ${data.filename}`, 'success');
      } else {
        addNotification(data.error || 'Failed to capture screenshot', 'error');
      }
    } catch (e) {
      addNotification('Screenshot error. Backend unreachable', 'error');
    }
  };

  return (
    <header className="h-20 border-b border-light-border dark:border-dark-border/60 bg-light-card/80 dark:bg-dark-card/60 backdrop-blur-xl px-4 sm:px-6 lg:px-8 flex items-center justify-between z-10 sticky top-0">
      {/* Left: Mobile Toggle + Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={toggleMobileMenu}
          className="lg:hidden p-2 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-light-border dark:border-dark-border text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors flex-shrink-0"
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="min-w-0">
          <h2 className="text-base sm:text-lg lg:text-xl font-bold tracking-tight text-slate-800 dark:text-white brand-font truncate">
            {title}
          </h2>
          <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 hidden sm:block truncate">
            {subtitle}
          </p>
        </div>
      </div>

      {/* Right: Quick Action Controls */}
      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
        {/* Backend Cloud Status Badge */}
        <button
          onClick={() => setActivePage('settings')}
          className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl border text-[11px] sm:text-xs font-semibold transition-all ${
            backendStatus.isConnected
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20'
          }`}
          title={
            backendStatus.isConnected
              ? `Backend Connected (${backendStatus.latency ? `${backendStatus.latency}ms` : 'Online'})`
              : 'Backend Disconnected - Click to configure in Settings'
          }
        >
          <Server className="h-3 w-3" />
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              backendStatus.isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
            }`}
          />
          <span className="hidden sm:inline">
            {backendStatus.isConnected ? (backendStatus.latency ? `${backendStatus.latency}ms` : 'Online') : 'Cloud Mode'}
          </span>
        </button>

        {/* FPS Badge (hidden on smallest screens) */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-light-border dark:border-dark-border text-xs font-semibold">
          <Activity className="h-3.5 w-3.5 text-accent animate-pulse" />
          <span className="text-slate-500 dark:text-slate-400">FPS:</span>
          <span className="text-accent font-bold">{liveState.fps || 30.0}</span>
        </div>

        {/* Camera Hardware Toggle */}
        <button
          onClick={liveState.camera_active ? stopCamera : startCamera}
          className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all duration-200 ${
            liveState.camera_active
              ? 'bg-accent/15 border-accent/40 text-accent hover:bg-accent/25'
              : 'bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-500 hover:text-slate-700 dark:hover:text-white'
          }`}
          title={liveState.camera_active ? "Turn Camera OFF" : "Turn Camera ON"}
        >
          {liveState.camera_active ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-accent"></span>
              </span>
              <span className="hidden xs:inline sm:inline">Camera ON</span>
            </>
          ) : (
            <>
              <CameraOff className="h-3.5 w-3.5" />
              <span className="hidden xs:inline sm:inline">Camera OFF</span>
            </>
          )}
        </button>

        {/* Quick Screenshot Button (hidden on mobile, feed has dedicated button) */}
        <button
          onClick={handleScreenshot}
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 hover:bg-slate-200 dark:hover:bg-slate-700/80 border border-light-border dark:border-dark-border text-xs font-semibold text-slate-700 dark:text-slate-200 transition-colors"
          title="Capture Snapshot"
        >
          <Camera className="h-3.5 w-3.5 text-primary" />
          <span>Capture</span>
        </button>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800/80 hover:bg-slate-200 dark:hover:bg-slate-700/80 border border-light-border dark:border-dark-border text-slate-700 dark:text-slate-200 transition-colors"
          title={theme === 'dark' ? "Switch to Light Mode" : "Switch to Dark Mode"}
          aria-label="Toggle Color Theme"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4 text-cyber-gold transition-transform hover:rotate-45" />
          ) : (
            <Moon className="h-4 w-4 text-primary transition-transform hover:-rotate-12" />
          )}
        </button>
      </div>
    </header>
  );
};
