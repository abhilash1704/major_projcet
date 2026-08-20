import { cn } from "../../../utils/cn";

export const IconButton = ({ icon: Icon, onClick, className, variant = "ghost", badge }) => {
  const baseStyles = "relative p-2 rounded-full transition-all duration-200 flex items-center justify-center focus-ring";
  const variants = {
    ghost: "text-slate-500 hover:text-slate-800 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-800",
    solid: "bg-white text-slate-700 shadow-soft hover:bg-slate-50 dark:bg-surface-dark dark:text-slate-200 border border-slate-200 dark:border-slate-700",
    primary: "bg-primary text-white hover:bg-primary-hover shadow-soft",
  };

  return (
    <button onClick={onClick} className={cn(baseStyles, variants[variant], className)}>
      <Icon size={20} />
      {badge && (
        <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-danger rounded-full border-2 border-white dark:border-surface-dark"></span>
      )}
    </button>
  );
};
