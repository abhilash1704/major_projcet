import { cn } from "../../utils/cn";

export const Button = ({ children, variant = "primary", className, ...props }) => {
  const baseStyles = "px-5 py-2.5 rounded-xl font-medium transition-all duration-200 focus-ring flex items-center justify-center gap-2";
  const variants = {
    primary: "bg-primary text-white hover:bg-primary-hover shadow-sm",
    secondary: "bg-white dark:bg-surface-dark text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800",
    danger: "bg-danger text-white hover:bg-red-700 shadow-sm",
    success: "bg-success text-white hover:bg-emerald-700 shadow-sm",
    ghost: "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800",
  };

  return (
    <button className={cn(baseStyles, variants[variant], className)} {...props}>
      {children}
    </button>
  );
};
