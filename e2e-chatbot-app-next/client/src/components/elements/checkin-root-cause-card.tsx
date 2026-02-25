import { memo } from 'react';

export type CheckinRootCauseCardProps = {
  zone: string;
  items: string[];
};

export const CheckinRootCauseCard = memo(function CheckinRootCauseCard({
  zone,
  items,
}: CheckinRootCauseCardProps) {
  return (
    <div
      className="rounded-lg border-2 border-red-500 bg-red-50 px-4 py-3 dark:border-red-500 dark:bg-red-950/30"
      data-response-type="checkin_root_cause"
    >
      <p className="font-semibold text-foreground">Root Cause{zone ? ` (${zone})` : ''}</p>
      <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-foreground">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
});
