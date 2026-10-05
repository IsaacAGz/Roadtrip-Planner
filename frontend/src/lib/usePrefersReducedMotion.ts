import { useReducedMotion } from "motion/react";

export function usePrefersReducedMotion(): boolean {
  const preference = useReducedMotion();
  if (preference !== null) {
    return preference;
  }
  if (typeof window === "undefined") {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
