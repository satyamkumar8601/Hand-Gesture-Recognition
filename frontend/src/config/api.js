/**
 * Centralized API & Backend URL Manager
 * Supports local development, Vercel deployments, and dynamic cloud backend switching.
 */

const STORAGE_KEY = 'omni_custom_api_url';

/**
 * Returns the currently active base API URL:
 * 1. Runtime override in localStorage (configured via Settings UI)
 * 2. Build-time environment variable VITE_API_URL (configured in Vercel dashboard)
 * 3. Default empty string '' (falls back to local relative proxy /api/...)
 */
export const getApiBaseUrl = () => {
  if (typeof window !== 'undefined') {
    const customUrl = localStorage.getItem(STORAGE_KEY);
    if (customUrl && customUrl.trim()) {
      return customUrl.trim().replace(/\/$/, '');
    }
  }

  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return envUrl.trim().replace(/\/$/, '');
  }

  return '';
};

/**
 * Returns the custom backend URL configured specifically in localStorage, if any.
 */
export const getCustomApiUrl = () => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(STORAGE_KEY) || '';
  }
  return '';
};

/**
 * Sets a custom backend URL in localStorage for live testing from Vercel.
 */
export const setCustomApiUrl = (url) => {
  if (typeof window !== 'undefined') {
    if (!url || !url.trim()) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, url.trim().replace(/\/$/, ''));
    }
    // Dispatch custom event to notify components across the app
    window.dispatchEvent(new Event('omni_backend_changed'));
  }
};

/**
 * Clears custom backend URL and reverts to default.
 */
export const clearCustomApiUrl = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(new Event('omni_backend_changed'));
  }
};

/**
 * Resolves a full API endpoint URL.
 * Example: apiUrl('/api/camera/status') -> 'https://backend.onrender.com/api/camera/status'
 */
export const apiUrl = (endpoint) => {
  const base = getApiBaseUrl();
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return base ? `${base}${path}` : path;
};

/**
 * Resolves the live video stream URL.
 * Automatically handles local development and cloud endpoints.
 */
export const getVideoFeedUrl = (landmarks = true, key = '') => {
  const base = getApiBaseUrl();
  const query = `landmarks=${landmarks}${key ? `&t=${key}` : ''}`;

  if (base) {
    return `${base}/video_feed?${query}`;
  }

  // Local development fallback
  const isLocal =
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.hostname === '');

  if (isLocal) {
    const host = window.location.hostname || '127.0.0.1';
    return `http://${host}:8000/video_feed?${query}`;
  }

  // Deployed to cloud without configured backend
  return null;
};

/**
 * Quick ping test to check if the backend API is reachable and measure latency.
 */
export const checkBackendHealth = async (testUrl = null) => {
  const targetBase = testUrl !== null ? testUrl.trim().replace(/\/$/, '') : getApiBaseUrl();
  const endpoint = targetBase ? `${targetBase}/api/health` : '/api/health';

  const startTime = performance.now();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 4000);

  try {
    const res = await fetch(endpoint, {
      signal: controller.signal,
      cache: 'no-store',
    });
    clearTimeout(timeoutId);
    const latency = Math.round(performance.now() - startTime);

    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      return { ok: true, latency, data };
    }
    return { ok: false, latency, error: `HTTP ${res.status}` };
  } catch (err) {
    clearTimeout(timeoutId);
    const latency = Math.round(performance.now() - startTime);
    const message = err.name === 'AbortError' ? 'Connection timed out' : 'Server unreachable';
    return { ok: false, latency, error: message };
  }
};
