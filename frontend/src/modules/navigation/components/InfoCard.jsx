import { cn } from "../../../utils/cn";

export const InfoCard = ({ title, icon: Icon, children, className, subtitle, status }) => {
  return (
    <div className={cn("bg-white dark:bg-surface-dark rounded-2xl p-5 border border-slate-200/80 dark:border-slate-800 shadow-soft transition-all duration-200", className)}>
      {title && (
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            {Icon && (
              <div className="p-2 rounded-xl bg-primary/10 text-primary dark:bg-primary/20">
                <Icon size={18} />
              </div>
            )}
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight">{title}</h3>
              {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>}
            </div>
          </div>
          {status && (
            <div className="ml-auto">
              {status}
            </div>
          )}
        </div>
      )}
      {children}
    </div>
  );
};
