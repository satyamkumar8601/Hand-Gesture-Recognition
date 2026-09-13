import React from 'react';

export const DashboardCard = ({ title, value, subtitle, icon: Icon, color = 'primary', trend }) => {
  const colorMap = {
    primary: 'from-primary/20 to-primary/5 text-primary border-primary/30',
    secondary: 'from-secondary/20 to-secondary/5 text-secondary border-secondary/30',
    accent: 'from-accent/20 to-accent/5 text-accent border-accent/30',
    cyber: 'from-cyan-500/20 to-cyan-500/5 text-cyber-cyan border-cyan-500/30',
    gold: 'from-amber-500/20 to-amber-500/5 text-cyber-gold border-amber-500/30',
  };

  const selectedColor = colorMap[color] || colorMap.primary;

  return (
    <div className="glass-card rounded-2xl p-5 relative overflow-hidden transition-all duration-300 hover:translate-y-[-2px] hover:shadow-lg border border-light-border dark:border-dark-border group">
      {/* Subtle top glow bar */}
      <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${selectedColor.split(' ')[0]} to-transparent`} />

      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {title}
          </p>
          <h3 className="text-2xl font-black mt-1 text-slate-900 dark:text-white brand-font tracking-tight">
            {value}
          </h3>
          {subtitle && (
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 flex items-center gap-1">
              {subtitle}
            </p>
          )}
        </div>

        <div className={`h-12 w-12 rounded-xl flex items-center justify-center border bg-gradient-to-br ${selectedColor} transition-transform group-hover:scale-110 duration-200`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>

      {trend && (
        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center text-xs font-semibold text-accent">
          {trend}
        </div>
      )}
    </div>
  );
};
