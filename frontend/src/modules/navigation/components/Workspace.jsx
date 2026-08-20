import { NavigationWorkspace } from "../../navigation-engine/components/NavigationWorkspace";
import { NavigationEngineProvider } from "../../navigation-engine/context/NavigationEngineContext";
import { RouteCard } from "./RouteCard";
import { TrafficCard } from "./TrafficCard";
import { SystemCard } from "./SystemCard";
import { AlternativeRoutesCard } from "./AlternativeRoutesCard";

import { RouteComparisonCard } from "./RouteComparisonCard";
import { RerouteNotification } from "./RerouteNotification";

export const Workspace = () => {
  return (
    <NavigationEngineProvider>
      <div className="flex-1 h-full w-full flex flex-col lg:flex-row overflow-hidden relative bg-background dark:bg-background-dark">
        {/* Center Navigation Workspace (~70% Width) */}
        <div className="flex-1 lg:w-[70%] h-full relative overflow-hidden flex flex-col border-r border-slate-200/60 dark:border-slate-800">
          <NavigationWorkspace />
        </div>

        {/* Right Information Panel (~30% Width) */}
        <aside className="w-full lg:w-[320px] xl:w-[360px] h-auto lg:h-full overflow-y-auto p-4 lg:p-6 bg-slate-50/50 dark:bg-surface-dark/40 flex flex-col gap-4 border-l border-slate-200/40 dark:border-slate-800 shrink-0 z-20">
          <RerouteNotification />
          <RouteCard />
          <AlternativeRoutesCard />
          <RouteComparisonCard />
          <TrafficCard />
          <SystemCard />
        </aside>
      </div>
    </NavigationEngineProvider>
  );
};
