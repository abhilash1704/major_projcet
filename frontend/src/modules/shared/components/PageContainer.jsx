import { cn } from "../../../utils/cn";

export const PageContainer = ({ children, className }) => {
  return (
    <div className={cn("max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 animate-fade-in flex flex-col h-full", className)}>
      {children}
    </div>
  );
};
