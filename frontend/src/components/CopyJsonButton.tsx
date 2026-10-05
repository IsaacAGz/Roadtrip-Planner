import { useState } from "react";

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
    <button
      type="button"
      onClick={handleCopy}
      className="bg-transparent px-0 py-1 font-sans text-sm font-medium text-ink underline decoration-line underline-offset-4 hover:text-primary-hover"
    >
      {copied ? "Copied" : label}
    </button>
  );
}
