import type { ValidationReport } from "../api/client";

interface ValidationSummaryProps {
  validation: ValidationReport;
  replanAttempts: number;
}

export function ValidationSummary({ validation, replanAttempts }: ValidationSummaryProps) {
  const approved = validation.approved;
  const hasWarnings = validation.warnings.length > 0;
  const tone = !approved
    ? "bg-pale-red text-pale-red-ink"
    : hasWarnings
      ? "bg-pale-yellow text-pale-yellow-ink"
      : "bg-pale-green text-pale-green-ink";
  const heading = !approved
    ? "Plan needs review"
    : hasWarnings
      ? "Plan approved with warnings"
      : "Plan approved";
  const statusLabel = !approved ? "Not approved" : hasWarnings ? "Approved with warnings" : "Approved";

  return (
    <section className={`rounded-xl border border-line p-6 ${tone}`}>
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="font-serif text-2xl leading-none tracking-[-0.03em]">{heading}</h2>
        <span className="rounded-full bg-surface/70 px-2 py-0.5 text-xs font-medium uppercase tracking-wide">
          {statusLabel}
        </span>
        <span className="font-mono text-sm">Replan attempts: {replanAttempts}</span>
      </div>

      {validation.hard_failures.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">Hard failures</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {validation.hard_failures.map((failure, index) => (
              <li key={`${failure.rule_id}-${index}`}>
                <strong>{failure.rule_id}</strong>: {failure.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasWarnings && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">Warnings</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {validation.warnings.map((warning, index) => (
              <li key={`${warning.rule_id}-${index}`}>
                <strong>{warning.rule_id}</strong>: {warning.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
