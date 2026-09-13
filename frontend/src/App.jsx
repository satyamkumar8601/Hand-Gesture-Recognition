import React, { useEffect } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { Notification } from './components/Notification';

// Pages
import { Dashboard } from './pages/Dashboard';
import { LiveRecognition } from './pages/LiveRecognition';
import { Dataset } from './pages/Dataset';
import { TrainModel } from './pages/TrainModel';
import { Analytics } from './pages/Analytics';
import { History } from './pages/History';
import { Settings } from './pages/Settings';

const MainLayout = () => {
  const { activePage, setActivePage } = useApp();

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ignore if user is typing in an input or textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

      if (e.key === '1') setActivePage('dashboard');
      if (e.key === '2') setActivePage('live');
      if (e.key === '3') setActivePage('dataset');
      if (e.key === '4') setActivePage('train');
      if (e.key === '5') setActivePage('analytics');
      if (e.key === '6') setActivePage('history');
      if (e.key === '7') setActivePage('settings');
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setActivePage]);

  const renderActivePage = () => {
    switch (activePage) {
      case 'dashboard':
        return <Dashboard />;
      case 'live':
        return <LiveRecognition />;
      case 'dataset':
        return <Dataset />;
      case 'train':
        return <TrainModel />;
      case 'analytics':
        return <Analytics />;
      case 'history':
        return <History />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-cyber-bg text-slate-100 flex flex-col antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
      <Notification />

      <div className="flex flex-1 overflow-hidden">
        {/* Left Navigation Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          <Navbar />
          
          <main className="flex-1 p-3 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
            {renderActivePage()}
          </main>

          <footer className="border-t border-cyber-border/40 py-4 px-8 text-center text-xs text-slate-500">
            <p>AI-Powered Hand Gesture Recognition System &bull; MediaPipe + Scikit-Learn &bull; Zero-Background Camera Active Release</p>
          </footer>
        </div>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <AppProvider>
      <MainLayout />
    </AppProvider>
  );
}
