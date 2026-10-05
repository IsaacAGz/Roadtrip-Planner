import { Link, useLocation } from "react-router-dom";

const focusRing =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine";

function textLinkClass(isCurrent: boolean): string {
  return [
    "rounded-full px-3 py-1.5 font-marketing text-sm text-pine transition-colors duration-200",
    focusRing,
    isCurrent ? "bg-sand-deep" : "hover:bg-sand-deep",
  ].join(" ");
}

export function SiteNav() {
  const { pathname, hash } = useLocation();
  const guideCurrent = pathname === "/" && hash === "#guide";
  const homeCurrent = pathname === "/" && !guideCurrent;
  const projectsCurrent = pathname === "/projects";
  const planCurrent = pathname === "/plan";

  return (
    <header className="pointer-events-none fixed inset-x-0 top-4 z-40 flex justify-center px-3">
      <nav
        aria-label="Primary"
        className="pointer-events-auto flex max-w-full items-center gap-1 overflow-x-auto rounded-full bg-sand px-2 py-1.5 font-marketing shadow-[0_10px_30px_rgb(28_58_46_/_0.12)] ring-1 ring-pine/10"
      >
        <Link
          to="/"
          aria-current={homeCurrent ? "page" : undefined}
          className={`${textLinkClass(homeCurrent)} font-display`}
        >
          Roadtrip Planner
        </Link>
        <Link
          to={{ pathname: "/", hash: "guide" }}
          aria-current={guideCurrent ? "page" : undefined}
          className={textLinkClass(guideCurrent)}
        >
          Guide
        </Link>
        <Link
          to="/projects"
          aria-current={projectsCurrent ? "page" : undefined}
          className={textLinkClass(projectsCurrent)}
        >
          Projects
        </Link>
        <Link
          to="/plan"
          aria-current={planCurrent ? "page" : undefined}
          className={[
            "rounded-full bg-amber px-3.5 py-1.5 text-sm font-medium text-pine transition-transform duration-200 hover:bg-amber-deep active:scale-[0.98]",
            focusRing,
            planCurrent ? "ring-2 ring-pine" : "",
          ].join(" ")}
        >
          Plan
        </Link>
      </nav>
    </header>
  );
}
