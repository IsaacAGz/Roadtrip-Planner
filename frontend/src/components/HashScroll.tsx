import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function HashScroll() {
  const { hash, pathname } = useLocation();

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!hash) {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
      return;
    }

    const target = document.getElementById(hash.slice(1));
    if (!target) {
      return;
    }

    target.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }, [hash, pathname]);

  return null;
}
