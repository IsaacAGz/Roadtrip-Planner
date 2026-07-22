interface DownloadJsonButtonProps {
  label?: string;
  value: unknown;
  filename: string;
}

export function DownloadJsonButton({
  label = "Download JSON",
  value,
  filename,
}: DownloadJsonButtonProps) {
  function handleDownload() {
    const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button
      type="button"
      onClick={handleDownload}
      className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
    >
      {label}
    </button>
  );
}
