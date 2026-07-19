import type { ReactNode } from "react";
import { useState } from "react";

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
    <div className="rounded-lg border border-slate-200">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
        aria-expanded={open}
      >
        <span>
          <span className="block text-sm font-semibold text-slate-900">{title}</span>
          {description && <span className="mt-0.5 block text-xs text-slate-500">{description}</span>}
        </span>
        <span className="text-slate-500">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="border-t border-slate-200 px-4 py-4">{children}</div>}
    </div>
  );
}
