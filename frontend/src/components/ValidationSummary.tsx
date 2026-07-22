import type { ValidationReport } from "../api/client";

interface ValidationSummaryProps {
  validation: ValidationReport;
  replanAttempts: number;
}

function groupByDay<T extends { day: number | null }>(items: T[]): Map<number | "general", T[]> {
  const groups = new Map<number | "general", T[]>();
  for (const item of items) {
    const key = item.day ?? "general";
    const existing = groups.get(key) ?? [];
    existing.push(item);
    groups.set(key, existing);
  }
  return groups;
}

export function ValidationSummary({ validation, replanAttempts }: ValidationSummaryProps) {
  const approved = validation.approved;
  const warningGroups = groupByDay(validation.warnings);

  return (
    <section
      className={`rounded-xl border p-4 ${
        approved ? "border-emerald-200 bg-emerald-50 text-emerald-950" : "border-amber-200 bg-amber-50 text-amber-950"
      }`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">{approved ? "Plan approved" : "Plan needs review"}</h2>
        <span className="rounded-full bg-white/70 px-3 py-1 text-xs font-medium uppercase">
          {approved ? "approved" : "not approved"}
        </span>
        <span className="text-sm">Replan attempts: {replanAttempts}</span>
      </div>

      {validation.hard_failures.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold">Hard failures</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {validation.hard_failures.map((failure, index) => (
              <li key={`${failure.rule_id}-${index}`}>
                <strong>{failure.rule_id}</strong>
                {failure.day != null ? ` (day ${failure.day})` : ""}: {failure.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {validation.warnings.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold">Warnings</h3>
          <div className="mt-2 space-y-3 text-sm">
            {[...warningGroups.entries()].map(([day, warnings]) => (
              <div key={String(day)}>
                <p className="font-medium">{day === "general" ? "General" : `Day ${day}`}</p>
                <ul className="mt-1 space-y-1">
                  {warnings.map((warning, index) => (
                    <li key={`${warning.rule_id}-${index}`}>
                      <strong>{warning.rule_id}</strong>: {warning.message}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
