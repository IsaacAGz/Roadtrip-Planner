import { useState } from "react";
import { quietButtonClass } from "../lib/ui";

interface CopyJsonButtonProps {
  label?: string;
  value: unknown;
}

export function CopyJsonButton({ label = "Copy JSON", value }: CopyJsonButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(JSON.stringify(value, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button type="button" onClick={handleCopy} className={quietButtonClass}>
      {copied ? "Copied" : label}
    </button>
  );
}
