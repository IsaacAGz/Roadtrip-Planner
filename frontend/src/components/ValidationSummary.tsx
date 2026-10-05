import type { ValidationReport } from "../api/client";

interface ValidationSummaryProps {
  validation: ValidationReport;
  replanAttempts: number;
}

export function ValidationSummary({ validation, replanAttempts }: ValidationSummaryProps) {
  const approved = validation.approved;

  return (
    <section
      className={`rounded-2xl p-5 ring-1 ${
        approved ? "bg-moss-wash text-pine ring-pine/15" : "bg-amber/15 text-pine ring-amber/40"
      }`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="font-display text-2xl leading-none tracking-[-0.03em]">
          {approved ? "Plan approved" : "Plan needs review"}
        </h2>
        <span className="rounded-full bg-paper/80 px-3 py-1 text-xs">
          {approved ? "Approved" : "Not approved"}
        </span>
        <span className="text-sm tabular-nums">Replan attempts: {replanAttempts}</span>
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

      {validation.warnings.length > 0 && (
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
