import { formatApiErrorMessage, type ApiErrorDetail } from "../api/client";

interface ErrorAlertProps {
  title?: string;
  message: string;
  detail?: ApiErrorDetail;
}

export function ErrorAlert({ title = "Request failed", message, detail }: ErrorAlertProps) {
  return (
    <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-900">
      <h2 className="font-semibold">{title}</h2>
      <p className="mt-2 text-sm">{message}</p>
      {detail && (
        <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-white/70 p-3 text-xs text-red-800">
          {formatApiErrorMessage(detail)}
        </pre>
      )}
    </section>
  );
}
