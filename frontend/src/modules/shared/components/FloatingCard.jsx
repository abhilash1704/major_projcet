import { cn } from "../../../utils/cn";

export const FloatingCard = ({ title, icon: Icon, children, className }) => {
  return (
    <div className={cn("bg-white dark:bg-surface-dark rounded-2xl shadow-float p-4 pointer-events-auto border border-slate-100 dark:border-slate-800 animate-fade-in", className)}>
      {title && (
        <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200 mb-3 flex items-center gap-2">
          {Icon && <Icon size={16} className="text-primary" />} 
          {title}
        </h4>
      )}
      {children}
    </div>
  );
};
