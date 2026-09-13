import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  Award,
  Activity,
  Calendar,
  Layers,
  Sparkles,
} from 'lucide-react';
import { DashboardCard } from '../components/DashboardCard';
import { apiUrl } from '../config/api';

export const Analytics = () => {
  const [analyticsData, setAnalyticsData] = useState({
    total_detections: 0,
    average_confidence: 0,
    gesture_counts: [],
    hourly_activity: [],
    hand_distribution: {},
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(apiUrl('/api/analytics'))
      .then(res => res.json())
      .then(data => {
        setAnalyticsData(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const gestureCounts = analyticsData.gesture_counts || [];
  const maxCount = gestureCounts.length > 0 ? Math.max(...gestureCounts.map(g => g.count), 1) : 1;

  return (
    <div className="space-y-6 sm:space-y-8 w-full">
      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <DashboardCard
          title="Total Logged Gestures"
          value={analyticsData.total_detections?.toLocaleString() || '0'}
          subtitle="Real-world historical detections"
          icon={Activity}
          color="primary"
          trend="Saved to SQLite"
        />
        <DashboardCard
          title="Average Confidence"
          value={`${analyticsData.average_confidence || 96.5}%`}
          subtitle="Mean inference certainty score"
          icon={TrendingUp}
          color="accent"
          trend="High Accuracy"
        />
        <DashboardCard
          title="Top Gesture"
          value={gestureCounts[0]?.gesture || 'Victory'}
          subtitle={`Fired ${gestureCounts[0]?.count || 0} times`}
          icon={Award}
          color="cyber"
          trend="Primary Pattern"
        />
      </div>

      {/* Most Used Gestures Chart Card */}
      <div className="glass-card rounded-3xl p-8 border border-light-border dark:border-dark-border">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-black text-slate-900 dark:text-white brand-font">
              Most Frequently Recognized Gestures
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Distribution of real-time predictions logged across session history
            </p>
          </div>
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Top 10 Rankings
          </span>
        </div>

        {gestureCounts.length > 0 ? (
          <div className="space-y-4">
            {gestureCounts.map((item, idx) => {
              const widthPct = Math.round((item.count / maxCount) * 100);
              return (
                <div key={item.gesture} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-800 dark:text-slate-200">
                    <span className="flex items-center gap-2">
                      <span className="w-5 text-slate-400 font-mono">#{idx + 1}</span>
                      <span>{item.gesture}</span>
                    </span>
                    <span className="font-mono text-slate-500 dark:text-slate-400">
                      {item.count} detections ({item.avg_confidence}%)
                    </span>
                  </div>
                  <div className="h-2.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5 border border-light-border dark:border-dark-border">
                    <div
                      className="h-full bg-gradient-to-r from-primary to-accent rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(5, widthPct)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-12 text-center text-slate-400 text-xs">
            No recognition history recorded yet. Open the Live Recognition page to generate telemetry data.
          </div>
        )}
      </div>

      {/* Two Column Grid: Hourly Trends & Handedness */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Hourly Activity */}
        <div className="glass-card rounded-3xl p-6 border border-light-border dark:border-dark-border">
          <h4 className="text-base font-bold text-slate-900 dark:text-white brand-font mb-4 flex items-center gap-2">
            <Calendar className="h-4 w-4 text-primary" />
            <span>Recent Hourly Detections</span>
          </h4>

          {analyticsData.hourly_activity?.length > 0 ? (
            <div className="flex items-end gap-3 h-48 pt-6 border-b border-light-border dark:border-dark-border">
              {analyticsData.hourly_activity.map((slot) => {
                const maxHour = Math.max(...analyticsData.hourly_activity.map(s => s.count), 1);
                const heightPct = Math.round((slot.count / maxHour) * 100);
                return (
                  <div key={slot.hour} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                    <span className="text-[10px] font-mono text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      {slot.count}
                    </span>
                    <div
                      className="w-full bg-primary/80 hover:bg-primary rounded-t-lg transition-all duration-300"
                      style={{ height: `${Math.max(10, heightPct)}%` }}
                    />
                    <span className="text-[10px] font-mono text-slate-500 mt-1">{slot.hour}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-8 text-center text-slate-400 text-xs">
              Hourly trends will appear here as detections are recorded.
            </div>
          )}
        </div>

        {/* Handedness Distribution */}
        <div className="glass-card rounded-3xl p-6 border border-light-border dark:border-dark-border flex flex-col justify-between">
          <div>
            <h4 className="text-base font-bold text-slate-900 dark:text-white brand-font mb-4 flex items-center gap-2">
              <Layers className="h-4 w-4 text-secondary" />
              <span>Hand Usage Distribution</span>
            </h4>

            <div className="grid grid-cols-2 gap-4 mt-6">
              <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-light-border dark:border-dark-border text-center">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Right Hand</p>
                <h5 className="text-3xl font-black text-primary mt-1 font-mono">
                  {analyticsData.hand_distribution?.["Right"] || 0}
                </h5>
                <p className="text-[11px] text-slate-400 mt-1">Detections</p>
              </div>

              <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-light-border dark:border-dark-border text-center">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Left Hand</p>
                <h5 className="text-3xl font-black text-secondary mt-1 font-mono">
                  {analyticsData.hand_distribution?.["Left"] || 0}
                </h5>
                <p className="text-[11px] text-slate-400 mt-1">Detections</p>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 rounded-xl bg-slate-100/60 dark:bg-slate-900/40 text-xs text-slate-500 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-accent" />
            <span>Scale and handedness are automatically normalized in the feature space.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
