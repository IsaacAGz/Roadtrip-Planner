import { useEffect } from "react";
import { App } from "../App";
import { SiteNav } from "../components/SiteNav";

export function PlannerPage() {
  useEffect(() => {
    document.title = "Plan a trip | Roadtrip Planner";
  }, []);

  return (
    <>
      <SiteNav />
      <div className="bg-sand pt-20">
        <App />
      </div>
    </>
  );
}
