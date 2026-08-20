import { cn } from "../../utils/cn";

export const Card = ({ children, className, ...props }) => {
  return (
    <div className={cn("bg-white dark:bg-surface-dark rounded-2xl shadow-soft p-6 border border-slate-100 dark:border-slate-800 transition-colors", className)} {...props}>
      {children}
    </div>
  );
};
