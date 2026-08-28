/**
 * LandingPage.jsx — Official AlgoRoutes Landing Page
 * Connected directly from abhilash1704/responsive-web-builder
 */
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../features/auth/AuthContext";

const MAP_IMAGE =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuDDwl9YgFvTTov_bw8Mi0-wd-Zi-9waCJhxAkGP4fKHlVyFG0sMTcStF4420SNTIQoYvliCYGY4e0zmhip8guVLhvxmsNOxPyEC1NudqTKAZ0ApneRPamvsh7UMQ8b7W2oEE7QA4m9hL5UTVDtLKYwBHMjb7ZTXrE1K7X0ZYQoiylPYvYCcD68DvYqNANO3ZMY6r7rZGmxuDBJa9iceL6AuOds3oQcgBrdQtXk9RBYp5pohM372bTk9lg";

const NAV = [
  { label: "Features", href: "#features" },
  { label: "Live Clustering", path: "/live-clustering" },
  { label: "Navigation Engine", path: "/navigation" },
  { label: "Analytics", href: "#metrics" },
];

const METRICS = [
  { value: "85.3%", label: "False Congestion Reduction", cls: "text-emerald-400 font-extrabold", icon: "hub" },
  { value: "<50ms", label: "A* Path Latency", cls: "text-blue-400 font-extrabold", icon: "bolt" },
  { value: "5-Sec", label: "Clustering Window", cls: "text-slate-100 font-extrabold", icon: "history_toggle_off" },
  { value: "500K+", label: "Graph Network Nodes", cls: "text-indigo-400 font-extrabold", icon: "account_tree" },
];

const FEATURES = [
  {
    icon: "scatter_plot",
    title: "Live Vehicle Clustering",
    body: "Continuous DBSCAN application over streaming telematic pings identifies stationary and crawling vehicle clusters, eliminating false positives from traffic lights.",
    glow: "bg-indigo-500/10 group-hover:bg-indigo-500/20",
    chip: "bg-indigo-950/60 border-indigo-500/30 text-indigo-300",
    path: "/live-clustering",
  },
  {
    icon: "route",
    title: "Dual A* & Dijkstra Routing",
    body: "Hybrid pathfinding engine that utilizes pre-computed Dijkstra heuristics for global orientation while employing A* for rapid local detours around active clusters.",
    glow: "bg-blue-500/10 group-hover:bg-blue-500/20",
    chip: "bg-blue-950/60 border-blue-500/30 text-blue-300",
    path: "/navigation",
  },
  {
    icon: "alt_route",
    title: "Traffic-Triggered Alternatives",
    body: "Automatically spawns and ranks alternative paths the moment edge weight decay (congestion) breaches threshold on primary routes.",
    glow: "bg-rose-500/10 group-hover:bg-rose-500/20",
    chip: "bg-rose-950/60 border-rose-500/30 text-rose-300",
    path: "/navigation",
  },
  {
    icon: "insights",
    title: "Precision Analytics",
    body: "Retrospective analysis tools correlating historic route suggestions against actual traversed times, enabling continuous tuning of node weights.",
    glow: "bg-emerald-500/10 group-hover:bg-emerald-500/20",
    chip: "bg-emerald-950/60 border-emerald-500/30 text-emerald-300",
    path: "/live-clustering",
  },
];

function Icon({ name, className = "" }) {
  return (
    <span className={`material-symbols-outlined leading-none ${className}`} aria-hidden="true">
      {name}
    </span>
  );
}

export const LandingPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const handleProtectedNav = (path) => {
    if (isAuthenticated) {
      navigate(path);
    } else {
      navigate(`/login?redirect=${encodeURIComponent(path)}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-blue-600 selection:text-white">
      {/* ── Top Fixed Navigation Bar ──────────────────────────────────── */}
      <header className="fixed top-0 z-50 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-4 px-5 sm:h-20 sm:px-6">
          <Link to="/" className="flex min-w-0 shrink-0 items-center gap-2.5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-md shadow-blue-500/25">
              <Icon name="route" className="text-[20px] text-white" />
            </span>
            <span className="truncate font-black text-xl tracking-tight text-white font-sans uppercase">
              Algo<span className="text-blue-500">Routes</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-6 lg:flex">
            {NAV.map((item) => (
              item.path ? (
                <button
                  key={item.label}
                  onClick={() => handleProtectedNav(item.path)}
                  className="text-sm font-semibold text-slate-300 transition-colors hover:text-blue-400 bg-transparent border-none cursor-pointer"
                >
                  {item.label}
                </button>
              ) : (
                <a
                  key={item.label}
                  href={item.href}
                  className="text-sm font-semibold text-slate-300 transition-colors hover:text-blue-400"
                >
                  {item.label}
                </a>
              )
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-3">
            <button
              onClick={() => navigate(isAuthenticated ? "/dashboard" : "/login")}
              className="hidden text-sm font-semibold text-slate-300 hover:text-white sm:inline-flex px-3 py-1.5"
            >
              {isAuthenticated ? "Dashboard" : "Sign In"}
            </button>
            <button
              onClick={() => handleProtectedNav("/dashboard")}
              className="flex items-center gap-2 rounded-full bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 text-sm font-bold shadow-lg shadow-blue-500/25 active:scale-95 transition-all"
            >
              <span>Launch Platform</span>
              <Icon name="arrow_forward" className="text-[18px]" />
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Hero & Content ────────────────────────────────────────── */}
      <main className="w-full pt-16 sm:pt-20">
        <div className="relative w-full overflow-hidden">
          {/* Ambient Glowing Background */}
          <div className="pointer-events-none absolute inset-x-0 top-0 z-0 flex h-[800px] justify-center overflow-hidden">
            <div className="absolute -top-40 h-[600px] w-[600px] rounded-full bg-blue-600/15 opacity-60 mix-blend-screen blur-[120px] lg:h-[800px] lg:w-[800px]" />
            <div className="absolute right-[-100px] top-20 h-[400px] w-[400px] rounded-full bg-emerald-500/15 opacity-40 mix-blend-screen blur-[100px] lg:h-[600px] lg:w-[600px]" />
          </div>

          {/* ── HERO SECTION ─────────────────────────────────────────── */}
          <section className="relative z-10 mx-auto grid w-full max-w-[1440px] grid-cols-1 items-center gap-10 px-5 pb-12 pt-10 sm:px-6 lg:grid-cols-12 lg:gap-8 lg:pb-28 lg:pt-20">
            <div className="z-20 flex flex-col items-start gap-5 lg:col-span-6 lg:pr-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-950/40 px-3.5 py-1.5 backdrop-blur-md">
                <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                <span className="text-[11px] font-bold uppercase tracking-widest text-emerald-300">
                  Live Traffic Intelligence Engine
                </span>
              </div>

              <h1 className="font-extrabold text-3xl sm:text-5xl lg:text-[3.2rem] lg:leading-[1.12] tracking-tight text-white">
                Next-Generation{" "}
                <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-emerald-400 bg-clip-text text-transparent">
                  Urban Navigation
                </span>{" "}
                &amp; Real-Time Clustering
              </h1>

              <p className="max-w-xl text-base leading-relaxed text-slate-300 font-normal">
                Powering urban mobility through continuous DBSCAN vehicle clustering, adaptive A* pathfinding, and
                instantaneous congestion state detection. We process real-world telematics to redefine routing
                efficiency across Bengaluru.
              </p>

              <div className="flex w-full flex-col gap-3 pt-3 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center sm:gap-4">
                <button
                  onClick={() => handleProtectedNav("/live-clustering")}
                  className="group flex items-center justify-center gap-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-7 py-3.5 font-bold text-sm shadow-xl shadow-blue-600/30 active:scale-95 transition-all"
                >
                  <span>Explore Live Clustering</span>
                  <Icon name="arrow_forward" className="text-[20px] transition-transform group-hover:translate-x-1" />
                </button>
                <button
                  onClick={() => handleProtectedNav("/navigation")}
                  className="flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900/80 hover:bg-slate-800 text-slate-200 hover:text-white px-7 py-3.5 font-bold text-sm backdrop-blur-md transition-all active:scale-95"
                >
                  View Navigation Engine
                </button>
              </div>
            </div>


            {/* Hero Visual Mockup */}
            <div className="relative z-10 flex aspect-[4/3] w-full items-center justify-center overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl backdrop-blur-2xl lg:col-span-6">
              <div
                className="absolute inset-0 bg-cover bg-center opacity-40 mix-blend-screen"
                style={{
                  backgroundImage: `url('${MAP_IMAGE}')`,
                  filter: "brightness(0.8) contrast(1.1)",
                }}
                role="img"
                aria-label="Stylized dark map of Silk Board Junction, Bengaluru"
              />
              <div className="absolute left-1/2 top-1/2 aspect-square w-[120%] -translate-x-1/2 -translate-y-1/2 animate-[spin_12s_linear_infinite] rounded-full border border-blue-500/20 bg-gradient-to-br from-blue-500/5 to-transparent [mask-image:conic-gradient(from_0deg,transparent_70%,black)]" />
              <div className="absolute left-1/2 top-1/2 aspect-square w-[80%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-blue-500/10" />
              <div className="absolute left-1/2 top-1/2 aspect-square w-[40%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-blue-500/10" />

              <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/90 px-3 py-1.5 backdrop-blur-md">
                    <Icon name="my_location" className="shrink-0 text-[16px] text-emerald-400" />
                    <span className="truncate text-[11px] font-bold uppercase tracking-wider text-slate-300">
                      Silk Board Junction, BLR
                    </span>
                  </div>
                  <div className="flex shrink-0 flex-col items-end rounded-xl border border-slate-800 bg-slate-900/90 px-3.5 py-1.5 backdrop-blur-md">
                    <span className="font-extrabold text-xl tracking-tight text-blue-400">
                      300
                    </span>
                    <span className="text-[10px] font-semibold uppercase text-slate-400">GPS Observations</span>
                  </div>
                </div>

                <div className="relative flex h-full w-full items-center justify-center">
                  <span className="absolute left-1/4 top-1/3 h-3.5 w-3.5 animate-pulse rounded-full bg-rose-500 shadow-[0_0_12px_#f43f5e]" />
                  <span className="absolute right-1/3 top-1/2 h-3.5 w-3.5 rounded-full bg-emerald-400 shadow-[0_0_12px_#34d399]" />
                  <span className="absolute bottom-1/4 left-1/2 grid h-5 w-5 place-items-center rounded-full border-2 border-indigo-400 bg-slate-900">
                    <span className="h-2 w-2 animate-ping rounded-full bg-indigo-400" />
                  </span>
                  
                  <span className="absolute left-[24%] top-[42%] rounded border border-indigo-500/40 bg-indigo-950/80 px-2 py-0.5 text-[10px] font-extrabold text-indigo-200 backdrop-blur-sm shadow-md">
                    Cluster 17 (Dense)
                  </span>
                  <span className="absolute right-[20%] top-[35%] rounded border border-emerald-500/40 bg-emerald-950/80 px-2 py-0.5 text-[10px] font-extrabold text-emerald-200 backdrop-blur-sm shadow-md">
                    Cluster 04 (Flow)
                  </span>
                </div>
              </div>
            </div>
          </section>

          {/* ── METRICS COUNTERS BAR ──────────────────────────────────── */}
          <section id="metrics" className="relative z-30 mx-auto -mt-2 w-full max-w-[1200px] px-5 sm:px-6">
            <div className="w-full overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-2xl backdrop-blur-xl">
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4 md:divide-x md:divide-slate-800">
                {METRICS.map((m) => (
                  <div key={m.label} className="group flex flex-col items-center justify-center p-2 text-center">
                    <Icon
                      name={m.icon}
                      className="mb-2 text-[26px] text-blue-400 opacity-80 transition-opacity group-hover:opacity-100"
                    />
                    <span className={`font-black text-2xl sm:text-[30px] ${m.cls}`}>{m.value}</span>
                    <span className="mt-1 text-[11px] font-bold uppercase tracking-wider leading-tight text-slate-400">{m.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* ── ALGORITHMIC FEATURES GRID ─────────────────────────────── */}
          <section id="features" className="z-20 mx-auto w-full max-w-[1440px] px-5 py-16 sm:px-6 lg:py-24">
            <div className="mb-10 flex flex-col">
              <h2 className="font-extrabold text-2xl sm:text-4xl text-white tracking-tight">Algorithmic Precision</h2>
              <p className="mt-2 max-w-2xl text-base text-slate-400">
                Modular subsystems designed for hyper-local traffic resolution and dynamic re-routing at scale.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              {FEATURES.map((f) => (
                <article
                  key={f.title}
                  onClick={() => handleProtectedNav(f.path)}
                  className="group relative flex flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 p-6 transition-all hover:bg-slate-800/60 hover:border-slate-700 cursor-pointer shadow-lg"
                >

                  <div className={`absolute right-0 top-0 h-32 w-32 rounded-bl-full blur-2xl transition-colors ${f.glow}`} />
                  <div className={`relative z-10 mb-4 grid h-11 w-11 place-items-center rounded-xl border ${f.chip}`}>
                    <Icon name={f.icon} className="text-[22px]" />
                  </div>
                  <h3 className="relative z-10 mb-2 font-bold text-xl text-white">{f.title}</h3>
                  <p className="relative z-10 text-sm leading-relaxed text-slate-300">{f.body}</p>
                </article>
              ))}
            </div>
          </section>
        </div>
      </main>

      {/* ── FOOTER ────────────────────────────────────────────────────── */}
      <footer className="w-full border-t border-slate-800 bg-slate-950 px-5 pb-8 pt-12 sm:px-6">
        <div className="mx-auto max-w-[1440px]">
          <div className="mb-10 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-5">
            <div className="space-y-4 lg:col-span-2">
              <div className="flex items-center gap-2.5">
                <span className="grid h-8 w-8 place-items-center rounded-xl bg-blue-600">
                  <Icon name="route" className="text-[18px] text-white" />
                </span>
                <span className="font-extrabold text-xl text-white tracking-tight">AlgoRoutes</span>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900 px-3 py-1">
                <Icon name="settings_input_component" className="text-[14px] text-emerald-400" />
                <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
                  Simulation-based live traffic analysis
                </span>
              </div>
              <p className="max-w-sm text-sm text-slate-400">
                Optimizing global logistics and urban mobility through real-time AI clustering and advanced predictive
                routing simulations.
              </p>
            </div>

            {[
              {
                title: "Product",
                links: [
                  { label: "Features", href: "#features" },
                  { label: "Live Clustering", path: "/live-clustering" },
                  { label: "Navigation Engine", path: "/navigation" },
                  { label: "Analytics", href: "#metrics" },
                ],
              },
              {
                title: "Developers",
                links: [
                  { label: "API Documentation", path: "/dashboard" },
                  { label: "SDKs", path: "/dashboard" },
                  { label: "Status", path: "/live-clustering" },
                ],
              },
              {
                title: "Company",
                links: [
                  { label: "About", path: "/" },
                  { label: "Blog", path: "/" },
                  { label: "Contact", path: "/" },
                ],
              },
            ].map((col) => (
              <div key={col.title} className="space-y-4">
                <h4 className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
                  {col.title}
                </h4>
                <nav className="flex flex-col gap-2">
                  {col.links.map((l) => (
                    l.path ? (
                      <Link key={l.label} to={l.path} className="text-sm font-semibold text-slate-400 hover:text-white transition-colors">
                        {l.label}
                      </Link>
                    ) : (
                      <a key={l.label} href={l.href} className="text-sm font-semibold text-slate-400 hover:text-white transition-colors">
                        {l.label}
                      </a>
                    )
                  ))}
                </nav>
              </div>
            ))}
          </div>

          <div className="flex flex-col items-center justify-between gap-4 border-t border-slate-800/80 pt-6 sm:flex-row">
            <span className="text-center text-xs font-semibold text-slate-500">
              © 2026 AlgoRoutes Intelligence. All rights reserved.
            </span>
            <div className="flex items-center gap-4">
              {["language", "terminal", "share"].map((i) => (
                <Icon key={i} name={i} className="cursor-pointer text-slate-400 hover:text-blue-400 transition-colors" />
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
