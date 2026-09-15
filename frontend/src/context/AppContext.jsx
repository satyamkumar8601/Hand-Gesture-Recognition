import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { apiUrl, getApiBaseUrl, checkBackendHealth } from '../config/api';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [activePage, setActivePage] = useState('dashboard');
  const [theme, setTheme] = useState(() => localStorage.getItem('omni_theme') || 'dark');
  const [notifications, setNotifications] = useState([]);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Backend Connectivity Status
  const [backendStatus, setBackendStatus] = useState({
    isConnected: false,
    latency: null,
    checkedAt: null,
    apiUrl: getApiBaseUrl(),
  });

  // Speech Synthesis & Sign-to-Speech Sentence Builder
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [sentenceWords, setSentenceWords] = useState([]);
  const lastSpokenRef = useRef({ text: '', time: 0 });

  const speakText = useCallback((text) => {
    if (!('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.error('Speech synthesis error:', e);
    }
  }, []);

  const speakGesture = useCallback((gestureName) => {
    if (!gestureName || gestureName === 'No Hand' || gestureName === 'Unknown') return;
    const now = Date.now();
    if (gestureName === lastSpokenRef.current.text && now - lastSpokenRef.current.time < 2200) {
      return;
    }
    lastSpokenRef.current = { text: gestureName, time: now };
    speakText(gestureName);
  }, [speakText]);

  const addGestureToSentence = useCallback((gestureName) => {
    if (!gestureName || gestureName === 'No Hand' || gestureName === 'Unknown') return;
    setSentenceWords(prev => {
      if (prev.length > 0 && prev[prev.length - 1] === gestureName) return prev;
      return [...prev, gestureName];
    });
  }, []);

  const speakSentence = useCallback(() => {
    if (sentenceWords.length === 0) return;
    speakText(sentenceWords.join(' '));
  }, [sentenceWords, speakText]);

  const removeLastWord = useCallback(() => {
    setSentenceWords(prev => prev.slice(0, -1));
  }, []);

  const clearSentence = useCallback(() => {
    setSentenceWords([]);
  }, []);
  
  // Real-time camera & prediction state
  const [liveState, setLiveState] = useState({
    fps: 0,
    hand_detected: false,
    hands_count: 0,
    primary_gesture: 'No Hand',
    confidence: 0,
    is_ml: false,
    icon: '✋',
    finger_states: { thumb: false, index: false, middle: false, ring: false, pinky: false },
    probabilities: {},
    camera_active: false,
    mode: 1,
    mode_name: 'HUD Analytics',
    mouse_enabled: false,
    canvas_color: 'Cyan',
    whiteboard_mode: false,
    rehab_grip_closure: 0,
    rehab_extended_fingers: 0,
  });

  // Model metadata state
  const [modelInfo, setModelInfo] = useState({
    loaded: false,
    model_name: 'Connecting...',
    accuracy: 0,
    classes_count: 0,
    total_samples: 0,
  });

  // Theme management
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
    localStorage.setItem('omni_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(prev => !prev);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  const addNotification = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random();
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 4000);
  }, []);

  // Backend Health and Connection Checker
  const checkConnection = useCallback(async () => {
    const res = await checkBackendHealth();
    setBackendStatus({
      isConnected: res.ok,
      latency: res.latency,
      checkedAt: new Date().toLocaleTimeString(),
      apiUrl: getApiBaseUrl(),
    });
    return res;
  }, []);

  // Fetch model information
  const refreshModelInfo = useCallback(async () => {
    try {
      const res = await fetch(apiUrl('/api/model/info'));
      if (res.ok) {
        const data = await res.json();
        setModelInfo(data);
        setBackendStatus(prev => ({ ...prev, isConnected: true, apiUrl: getApiBaseUrl() }));
      } else {
        setBackendStatus(prev => ({ ...prev, isConnected: false }));
      }
    } catch (e) {
      setBackendStatus(prev => ({ ...prev, isConnected: false }));
    }
  }, []);

  useEffect(() => {
    checkConnection();
    refreshModelInfo();

    const handleBackendChanged = () => {
      checkConnection();
      refreshModelInfo();
    };

    window.addEventListener('omni_backend_changed', handleBackendChanged);
    return () => window.removeEventListener('omni_backend_changed', handleBackendChanged);
  }, [checkConnection, refreshModelInfo]);

  // Turn off camera hardware immediately when user exits the website or closes tab
  useEffect(() => {
    const handleExit = () => {
      try {
        const stopUrl = apiUrl('/api/camera/stop');
        if (navigator.sendBeacon) {
          navigator.sendBeacon(stopUrl);
        } else {
          fetch(stopUrl, { method: 'POST', keepalive: true });
        }
      } catch (err) {}
    };

    window.addEventListener('pagehide', handleExit);
    window.addEventListener('beforeunload', handleExit);

    return () => {
      window.removeEventListener('pagehide', handleExit);
      window.removeEventListener('beforeunload', handleExit);
    };
  }, []);

  // Adaptive High-Speed Telemetry Poller:
  // - 150ms when camera is active for ultra-responsive gesture detection & finger tracking
  // - 2500ms when camera is standby to conserve CPU / cloud bandwidth
  // - Paused when tab is hidden in background
  useEffect(() => {
    let timerId = null;
    let isSubscribed = true;

    const poll = async () => {
      if (document.hidden) {
        timerId = setTimeout(poll, 2000);
        return;
      }

      try {
        const res = await fetch(apiUrl('/api/camera/status'));
        if (res.ok && isSubscribed) {
          const data = await res.json();
          setBackendStatus(prev => {
            if (!prev.isConnected) {
              return { ...prev, isConnected: true, apiUrl: getApiBaseUrl() };
            }
            return prev;
          });
          setLiveState(prev => {
            // When browser webcam is active, frame predictions and camera_active come directly
            // from the client-side webcam feed. Do not overwrite gesture or active status from idle OpenCV.
            if (prev.is_browser_cam) {
              return {
                ...prev,
                mode: data.mode !== undefined ? data.mode : prev.mode,
                mode_name: data.mode_name || prev.mode_name,
                canvas_color: data.canvas_color || prev.canvas_color,
                whiteboard_mode: data.whiteboard_mode !== undefined ? data.whiteboard_mode : prev.whiteboard_mode,
                mouse_enabled: data.mouse_enabled !== undefined ? data.mouse_enabled : prev.mouse_enabled,
              };
            }

            const gestureChanged = prev.primary_gesture !== data.primary_gesture;
            const handChanged = prev.hand_detected !== data.hand_detected;
            const cameraChanged = prev.camera_active !== data.camera_active;
            const modeChanged = prev.mode !== data.mode;
            const mouseChanged = prev.mouse_enabled !== data.mouse_enabled;
            const whiteboardChanged = prev.whiteboard_mode !== data.whiteboard_mode;
            const colorChanged = prev.canvas_color !== data.canvas_color;
            const confDiff = Math.abs((prev.confidence || 0) - (data.confidence || 0)) >= 5;
            const fpsDiff = Math.abs((prev.fps || 0) - (data.fps || 0)) >= 3;
            const gripDiff = Math.abs((prev.rehab_grip_closure || 0) - (data.rehab_grip_closure || 0)) >= 4;

            if (
              !gestureChanged &&
              !handChanged &&
              !cameraChanged &&
              !modeChanged &&
              !mouseChanged &&
              !whiteboardChanged &&
              !colorChanged &&
              !confDiff &&
              !fpsDiff &&
              !gripDiff
            ) {
              return prev; // Skip re-rendering when telemetry has not meaningfully changed
            }
            return data;
          });
        } else if (isSubscribed) {
          setBackendStatus(prev => (prev.isConnected ? { ...prev, isConnected: false } : prev));
        }
      } catch (e) {
        if (isSubscribed) {
          setBackendStatus(prev => (prev.isConnected ? { ...prev, isConnected: false } : prev));
        }
      }

      if (isSubscribed) {
        const delay = liveState.camera_active ? 280 : 2500;
        timerId = setTimeout(poll, delay);
      }
    };

    const handleVisibilityChange = () => {
      if (!document.hidden && isSubscribed) {
        poll();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    timerId = setTimeout(poll, 100);

    return () => {
      isSubscribed = false;
      if (timerId) clearTimeout(timerId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [liveState.camera_active]);

  const isStartingCameraRef = useRef(false);
  const stopCameraTimeoutRef = useRef(null);

  // Fast optimistic camera start/stop helpers wrapped in useCallback with StrictMode protection
  const startCamera = useCallback(async (quiet = false) => {
    if (isStartingCameraRef.current) return;
    isStartingCameraRef.current = true;

    if (stopCameraTimeoutRef.current) {
      clearTimeout(stopCameraTimeoutRef.current);
      stopCameraTimeoutRef.current = null;
    }
    setLiveState(prev => ({ ...prev, camera_active: true }));
    try {
      const res = await fetch(apiUrl('/api/camera/start'), { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success !== false) {
        setLiveState(prev => ({ ...prev, camera_active: true }));
        if (!quiet) addNotification('Backend camera activated', 'success');
      } else {
        setLiveState(prev => ({ ...prev, camera_active: false }));
        if (!quiet) addNotification(data.error || 'Failed to start camera hardware', 'error');
      }
    } catch (e) {
      setLiveState(prev => ({ ...prev, camera_active: false }));
      if (!quiet) addNotification('Camera start request failed. Is the backend running?', 'error');
    } finally {
      isStartingCameraRef.current = false;
    }
  }, [addNotification]);

  const stopCamera = useCallback(async (immediate = false) => {
    if (stopCameraTimeoutRef.current) {
      clearTimeout(stopCameraTimeoutRef.current);
      stopCameraTimeoutRef.current = null;
    }

    const executeStop = async () => {
      setLiveState(prev => ({ ...prev, camera_active: false }));
      try {
        await fetch(apiUrl('/api/camera/stop'), { method: 'POST' });
      } catch (e) {
        // ignore
      }
    };

    if (immediate) {
      await executeStop();
    } else {
      // 800ms debounce prevents StrictMode mount-unmount-mount churn
      stopCameraTimeoutRef.current = setTimeout(executeStop, 800);
    }
  }, []);

  // Studio Mode Management
  const setStudioMode = async (modeId) => {
    const modeNames = { 1: 'HUD Analytics', 2: 'Air Canvas', 3: 'Virtual Mouse', 4: 'Biometrics & Rehab' };
    setLiveState(prev => ({ ...prev, mode: modeId, mode_name: modeNames[modeId] || 'Mode' }));
    addNotification(`Active: ${modeNames[modeId]}`, 'success');
    try {
      await fetch(apiUrl(`/api/studio/mode/${modeId}`), { method: 'POST' });
    } catch (e) {
      // Background acknowledge
    }
  };

  // Air Canvas Actions
  const clearCanvas = async () => {
    window.dispatchEvent(new CustomEvent('omni_clear_canvas'));
    addNotification('Canvas Cleared', 'info');
    try {
      await fetch(apiUrl('/api/canvas/clear'), { method: 'POST' });
    } catch (e) {}
  };

  const undoCanvas = async () => {
    window.dispatchEvent(new CustomEvent('omni_undo_canvas'));
    addNotification('Stroke Undone', 'info');
    try {
      await fetch(apiUrl('/api/canvas/undo'), { method: 'POST' });
    } catch (e) {}
  };

  const setCanvasColor = async (colorName) => {
    setLiveState(prev => ({ ...prev, canvas_color: colorName }));
    try {
      await fetch(apiUrl('/api/canvas/color'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ color: colorName }),
      });
      addNotification(`Brush Color: ${colorName}`, 'info');
    } catch (e) {}
  };

  const toggleWhiteboard = async () => {
    try {
      const res = await fetch(apiUrl('/api/canvas/whiteboard'), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setLiveState(prev => ({ ...prev, whiteboard_mode: data.whiteboard_mode }));
        addNotification(data.whiteboard_mode ? 'Whiteboard Enabled' : 'Camera Background Enabled', 'info');
      }
    } catch (e) {}
  };

  const setBrushSize = async (size) => {
    try {
      await fetch(apiUrl('/api/canvas/brush'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ size }),
      });
    } catch (e) {}
  };

  // Virtual Mouse Actions
  const toggleVirtualMouse = async () => {
    try {
      const res = await fetch(apiUrl('/api/mouse/toggle'), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setLiveState(prev => ({ ...prev, mouse_enabled: data.mouse_enabled }));
        addNotification(data.mouse_enabled ? 'Virtual Mouse Activated' : 'Virtual Mouse Paused', 'info');
      }
    } catch (e) {}
  };

  // Auto-speak gesture when voice announcement is enabled
  useEffect(() => {
    if (voiceEnabled && liveState.camera_active && liveState.hand_detected) {
      speakGesture(liveState.primary_gesture);
    }
  }, [voiceEnabled, liveState.primary_gesture, liveState.camera_active, liveState.hand_detected, speakGesture]);

  return (
    <AppContext.Provider
      value={{
        activePage,
        setActivePage: (page) => {
          setActivePage(page);
          setIsMobileMenuOpen(false); // Auto-close mobile drawer on navigation
        },
        theme,
        toggleTheme,
        liveState,
        setLiveState,
        modelInfo,
        refreshModelInfo,
        backendStatus,
        checkConnection,
        notifications,
        addNotification,
        startCamera,
        stopCamera,
        setStudioMode,
        clearCanvas,
        undoCanvas,
        setCanvasColor,
        toggleWhiteboard,
        setBrushSize,
        toggleVirtualMouse,
        isMobileMenuOpen,
        setIsMobileMenuOpen,
        toggleMobileMenu,
        closeMobileMenu,
        voiceEnabled,
        setVoiceEnabled,
        sentenceWords,
        speakGesture,
        speakText,
        addGestureToSentence,
        speakSentence,
        removeLastWord,
        clearSentence,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => useContext(AppContext);
