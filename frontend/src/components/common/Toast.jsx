import { cn } from "../../utils/cn";

export const Toast = ({ message, type = "success", isVisible }) => {
  if (!isVisible) return null;

  const styles = {
    success: "bg-success text-white",
    error: "bg-danger text-white",
    warning: "bg-warning text-white",
    info: "bg-primary text-white"
  };

  return (
    <div className={cn("fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 transition-all duration-300 transform", styles[type])}>
      <span className="font-medium text-sm">{message}</span>
    </div>
  );
};
