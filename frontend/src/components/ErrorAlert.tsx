import { formatApiErrorMessage, type ApiErrorDetail } from "../api/client";

interface ErrorAlertProps {
  title?: string;
  message: string;
  detail?: ApiErrorDetail;
}

export function ErrorAlert({ title = "Request failed", message, detail }: ErrorAlertProps) {
  return (
    <section className="rounded-2xl bg-clay-wash p-5 text-clay ring-1 ring-clay/20" role="alert">
      <h2 className="font-display text-2xl leading-none tracking-[-0.03em]">{title}</h2>
      <p className="mt-3 max-w-prose text-sm leading-relaxed">{message}</p>
      {detail && (
        <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-paper/80 p-3 text-xs text-clay">
          {formatApiErrorMessage(detail)}
        </pre>
      )}
    </section>
  );
}
