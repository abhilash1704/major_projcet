import { Cpu, Server, Monitor, Database, Map, Navigation } from "lucide-react";
import { InfoCard } from "./InfoCard";

export const SystemCard = () => {
  const statusList = [
    { name: "Backend", status: "Connected", isLive: true, icon: Server },
    { name: "Frontend", status: "Connected", isLive: true, icon: Monitor },
    { name: "Database", status: "Connected", isLive: true, icon: Database },
    { name: "Map Engine", status: "Waiting", isLive: false, icon: Map },
    { name: "GPS Service", status: "Waiting", isLive: false, icon: Navigation },
  ];

  return (
    <InfoCard title="System Status" icon={Cpu} subtitle="Services Health">
      <div className="space-y-2.5 text-xs">
        {statusList.map((item, i) => (
          <div key={i} className="flex items-center justify-between py-1.5 px-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <item.icon size={14} className="text-slate-400" />
              <span className="font-medium text-slate-700 dark:text-slate-300">{item.name}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${item.isLive ? 'bg-success' : 'bg-warning'}`}></span>
              <span className={`font-semibold ${item.isLive ? 'text-success' : 'text-warning'}`}>{item.status}</span>
            </div>
          </div>
        ))}
      </div>
    </InfoCard>
  );
};
