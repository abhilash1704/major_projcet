import { Link } from 'react-router-dom';

function Icon({ name, className = '' }) {
  return (
    <span className={`material-symbols-outlined leading-none ${className}`} aria-hidden="true">
      {name}
    </span>
  );
}

export const AuthLayout = ({ children, title, subtitle }) => {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-blue-600 selection:text-white flex flex-col justify-between relative overflow-hidden">
      {/* Ambient Glowing Background */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-0 flex h-[600px] justify-center overflow-hidden">
        <div className="absolute -top-30 h-[500px] w-[500px] rounded-full bg-blue-600/20 opacity-70 mix-blend-screen blur-[120px]" />
        <div className="absolute right-[-80px] top-10 h-[350px] w-[350px] rounded-full bg-emerald-500/15 opacity-50 mix-blend-screen blur-[100px]" />
      </div>

      {/* Header Bar */}
      <header className="relative z-10 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-5 sm:h-20 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-md shadow-blue-500/25">
              <Icon name="route" className="text-[20px] text-white" />
            </span>
            <span className="truncate font-black text-xl tracking-tight text-white font-sans uppercase">
              Route<span className="text-blue-500">Flow</span>
            </span>
          </Link>
          <Link
            to="/"
            className="text-xs font-semibold text-slate-400 hover:text-white transition-colors flex items-center gap-1"
          >
            <Icon name="arrow_back" className="text-[16px]" />
            Back to Home
          </Link>
        </div>
      </header>

      {/* Main Body */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-extrabold text-white tracking-tight">{title}</h1>
              {subtitle && <p className="text-sm text-slate-400 mt-1.5">{subtitle}</p>}
            </div>
            {children}
          </div>
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="relative z-10 w-full border-t border-slate-800/80 py-4 text-center text-xs text-slate-500">
        © 2026 RouteFlow Intelligence Platform. All rights reserved.
      </footer>
    </div>
  );
};
