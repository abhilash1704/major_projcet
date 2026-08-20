import { Link } from "react-router-dom";
import { Button } from "../../components/common/Button";

export const Landing = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="h-20 bg-white border-b border-slate-200 flex items-center justify-between px-8">
        <h1 className="text-2xl font-bold text-primary">RouteFlow</h1>
        <div className="flex items-center gap-4">
          <Link to="/login" className="text-slate-600 font-medium hover:text-slate-900">Login</Link>
          <Link to="/register"><Button>Get Started</Button></Link>
        </div>
      </header>
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4">
        <h2 className="text-5xl font-extrabold text-slate-900 tracking-tight mb-6 max-w-4xl">
          Dynamic Traffic Routing Optimization
        </h2>
        <p className="text-xl text-slate-500 mb-10 max-w-2xl">
          Intelligent navigation using real-time vehicle clustering and advanced routing algorithms.
        </p>
        <div className="flex gap-4">
          <Link to="/register"><Button className="text-lg px-8 py-3">Start Navigating</Button></Link>
        </div>
      </main>
    </div>
  );
};
