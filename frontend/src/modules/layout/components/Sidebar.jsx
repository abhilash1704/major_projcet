import { Link, useLocation } from "react-router-dom";
import { Home, LayoutDashboard, Map, Users, Compass, Clock, Settings, UserCircle, LogOut, X } from "lucide-react";
import { cn } from "../../../utils/cn";
import { IconButton } from "../../shared/components/IconButton";

export const Sidebar = ({ isOpen, setIsOpen }) => {
  const location = useLocation();

  const navItems = [
    { name: "Home", path: "/", icon: Home },
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Navigation", path: "/navigation", icon: Map },
    { name: "Live Clustering", path: "/live-clustering", icon: Users },
    { name: "Routes", path: "/routes", icon: Compass },
    { name: "History", path: "/history", icon: Clock },
    { name: "Settings", path: "/settings", icon: Settings },
    { name: "Profile", path: "/profile", icon: UserCircle },
  ];

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/50 z-40 lg:hidden animate-fade-in"
          onClick={() => setIsOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      <aside className={cn(
        "fixed lg:static top-0 left-0 h-screen z-50 bg-white dark:bg-surface-dark border-r border-slate-200 dark:border-slate-800 flex flex-col transition-all duration-300",
        "w-64 lg:w-20 lg:hover:w-64 group shadow-sm",
        isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        <div className="h-16 flex items-center justify-between px-6 border-b border-slate-100 dark:border-slate-800">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-9 h-9 bg-primary rounded-xl flex items-center justify-center shrink-0 shadow-md shadow-primary/20">
              <span className="text-white font-bold text-lg">A</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight lg:hidden group-hover:block whitespace-nowrap">
              Algo<span className="text-primary">Routes</span>
            </h1>
          </Link>
          <IconButton icon={X} onClick={() => setIsOpen(false)} className="lg:hidden" />
        </div>

        <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-1.5 px-3">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.name}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={cn(
                  "flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200",
                  isActive 
                    ? "bg-primary text-white shadow-md shadow-primary/25" 
                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100"
                )}
              >
                <item.icon size={20} className={isActive ? "text-white shrink-0" : "text-slate-400 shrink-0 group-hover:text-slate-600 dark:group-hover:text-slate-200"} />
                <span className="lg:hidden group-hover:block whitespace-nowrap">{item.name}</span>
              </Link>
            );
          })}
        </div>

        <div className="p-4 border-t border-slate-100 dark:border-slate-800">
          <button className="flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-sm text-slate-600 dark:text-slate-400 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-danger dark:hover:text-red-400 w-full transition-colors justify-start">
            <LogOut size={20} className="shrink-0" />
            <span className="lg:hidden group-hover:block whitespace-nowrap">Logout</span>
          </button>
        </div>
      </aside>
    </>
  );
};
