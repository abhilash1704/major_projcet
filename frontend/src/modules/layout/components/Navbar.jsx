import { Search, Menu } from "lucide-react";
import { IconButton } from "../../shared/components/IconButton";
import { ThemeToggle } from "../../shared/components/ThemeToggle";
import { NotificationButton } from "../../shared/components/NotificationButton";
import { ProfileMenu } from "../../shared/components/ProfileMenu";

export const Navbar = ({ onMenuClick }) => {
  return (
    <header className="h-16 bg-white dark:bg-surface-dark border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 lg:px-6 sticky top-0 z-30 transition-colors shadow-xs">
      <div className="flex items-center gap-3">
        <IconButton icon={Menu} onClick={onMenuClick} className="lg:hidden" />
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-primary rounded-xl flex items-center justify-center lg:hidden shadow-sm">
            <span className="text-white font-bold text-base">R</span>
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white leading-tight">RouteFlow</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 hidden sm:block">Intelligent Navigation Platform</p>
          </div>
        </div>
      </div>
      
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="hidden md:flex items-center gap-2 bg-slate-50 dark:bg-slate-800/80 px-3.5 py-1.5 rounded-full border border-slate-200 dark:border-slate-700/70 text-sm text-slate-500 dark:text-slate-400 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/60 transition-colors">
          <Search size={15} />
          <span className="text-xs font-medium">Search locations, routes...</span>
          <span className="bg-white dark:bg-slate-900 px-1.5 py-0.5 rounded text-[10px] font-semibold border border-slate-200 dark:border-slate-700 ml-1 text-slate-400">⌘K</span>
        </div>
        <IconButton icon={Search} className="md:hidden" />
        <NotificationButton hasUnread={true} />
        <ThemeToggle />
        <div className="w-px h-6 bg-slate-200 dark:bg-slate-700 mx-1"></div>
        <ProfileMenu />
      </div>
    </header>
  );
};
