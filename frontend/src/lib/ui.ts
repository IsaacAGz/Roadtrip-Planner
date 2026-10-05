export const focusRing =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine";

export const panelClass =
  "rounded-2xl bg-paper text-pine shadow-[0_16px_40px_rgb(28_58_46_/_0.06)] ring-1 ring-pine/10";

export const fieldClass = `w-full rounded-lg border border-pine/15 bg-sand px-3 py-2 text-pine transition duration-200 placeholder:text-pine-muted/80 focus-visible:border-amber disabled:cursor-not-allowed disabled:bg-sand-deep disabled:text-pine-muted ${focusRing}`;

export const primaryButtonClass = `inline-flex items-center justify-center rounded-full bg-amber px-5 py-2.5 text-sm font-medium text-pine transition duration-200 hover:bg-amber-deep active:scale-[0.98] disabled:cursor-not-allowed disabled:bg-sand-deep disabled:text-pine-muted disabled:hover:bg-sand-deep ${focusRing}`;

export const quietButtonClass = `inline-flex items-center justify-center rounded-full bg-paper px-3 py-1.5 text-sm font-medium text-pine ring-1 ring-pine/15 transition duration-200 hover:bg-sand-deep active:scale-[0.98] ${focusRing}`;
