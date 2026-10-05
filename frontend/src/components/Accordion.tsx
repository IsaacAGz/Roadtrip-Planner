import type { ReactNode } from "react";
import { useState } from "react";
import { focusRing } from "../lib/ui";

interface AccordionProps {
  title: string;
  description?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

export function Accordion({
  title,
  description,
  defaultOpen = false,
  children,
}: AccordionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl bg-sand ring-1 ring-pine/10">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition duration-200 hover:bg-sand-deep/60 ${focusRing}`}
        aria-expanded={open}
      >
        <span>
          <span className="block text-sm font-medium text-pine">{title}</span>
          {description && <span className="mt-0.5 block text-xs text-pine-muted">{description}</span>}
        </span>
        <span className="font-display text-lg text-pine-muted" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>
      {open && <div className="border-t border-pine/10 px-4 py-4">{children}</div>}
    </div>
  );
}
