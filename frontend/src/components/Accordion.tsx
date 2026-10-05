import { useId, useState, type ReactNode } from "react";

interface AccordionProps {
  title: string;
  description?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

function DisclosureMark({ open }: { open: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="shrink-0 text-ink">
      <path d="M3 8h10" stroke="currentColor" strokeWidth="1.5" />
      {open ? null : <path d="M8 3v10" stroke="currentColor" strokeWidth="1.5" />}
    </svg>
  );
}

export function Accordion({
  title,
  description,
  defaultOpen = false,
  children,
}: AccordionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <div className="border-b border-line">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-4 py-3 text-left"
        aria-expanded={open}
        aria-controls={panelId}
      >
        <span>
          <span className="block text-sm font-medium text-ink">{title}</span>
          {description && <span className="mt-0.5 block text-xs text-muted">{description}</span>}
        </span>
        <DisclosureMark open={open} />
      </button>
      {open && (
        <div id={panelId} className="pb-4">
          {children}
        </div>
      )}
    </div>
  );
}
