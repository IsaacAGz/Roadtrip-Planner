import { formatApiErrorMessage, type ApiErrorDetail } from "../api/client";

interface ErrorAlertProps {
  title?: string;
  message: string;
  detail?: ApiErrorDetail;
}

export function ErrorAlert({ title = "Request failed", message, detail }: ErrorAlertProps) {
  return (
    <section className="rounded-xl border border-line bg-pale-red p-6 text-pale-red-ink">
      <p className="text-xs font-medium uppercase tracking-wide">Error</p>
      <h2 className="mt-1 font-serif text-2xl leading-none tracking-[-0.03em]">{title}</h2>
      <p className="mt-3 text-sm">{message}</p>
      {detail && (
        <pre className="mt-4 whitespace-pre-wrap rounded-md bg-surface p-3 font-mono text-xs text-pale-red-ink">
          {formatApiErrorMessage(detail)}
        </pre>
      )}
    </section>
  );
}
