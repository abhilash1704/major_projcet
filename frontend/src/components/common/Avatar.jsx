import { cn } from "../../utils/cn";

export const Avatar = ({ src, fallback, size = "md", className, ...props }) => {
  const sizes = {
    sm: "w-8 h-8 text-xs",
    md: "w-10 h-10 text-sm",
    lg: "w-12 h-12 text-base",
  };

  return (
    <div className={cn("relative rounded-full overflow-hidden bg-slate-200 flex items-center justify-center shrink-0", sizes[size], className)} {...props}>
      {src ? (
        <img src={src} alt="Avatar" className="w-full h-full object-cover" />
      ) : (
        <span className="font-medium text-slate-600">{fallback}</span>
      )}
    </div>
  );
};
