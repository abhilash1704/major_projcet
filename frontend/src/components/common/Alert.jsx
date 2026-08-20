import { cn } from "../../utils/cn";
import { AlertCircle, CheckCircle, Info, AlertTriangle } from "lucide-react";

export const Alert = ({ type = "info", title, message, className }) => {
  const styles = {
    info: "bg-primary-light text-primary border-primary/20",
    success: "bg-success-light text-success border-success/20",
    warning: "bg-warning-light text-warning border-warning/20",
    danger: "bg-danger-light text-danger border-danger/20",
  };

  const icons = {
    info: <Info size={20} />,
    success: <CheckCircle size={20} />,
    warning: <AlertTriangle size={20} />,
    danger: <AlertCircle size={20} />,
  };

  return (
    <div className={cn("flex items-start p-4 rounded-xl border animate-fade-in", styles[type], className)}>
      <div className="shrink-0 mr-3 mt-0.5">{icons[type]}</div>
      <div>
        {title && <h4 className="font-semibold text-sm mb-1">{title}</h4>}
        <p className="text-sm opacity-90">{message}</p>
      </div>
    </div>
  );
};
