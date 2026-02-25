import { useTableData } from '@/hooks/useTableData';
import { useTableRefresh } from '@/contexts/TableRefreshContext';

function avgCheckinColor(mins: number): 'green' | 'amber' | 'red' {
  if (mins <= 5) return 'green';
  if (mins <= 20) return 'amber';
  return 'red';
}

function getColIndex(columns: string[], name: string): number {
  const lower = name.toLowerCase();
  return columns.findIndex((c) => c.toLowerCase() === lower);
}

function getCell(row: unknown[], colIndex: number): unknown {
  return colIndex >= 0 ? row[colIndex] : undefined;
}

function MetricCard({
  value,
  label,
  subLabel,
  color,
  arcPercent,
}: {
  value: string;
  label: string;
  subLabel?: string;
  color: 'green' | 'amber' | 'red' | 'teal';
  arcPercent: number;
}) {
  const colorClasses = {
    green: 'text-emerald-600 dark:text-emerald-400',
    amber: 'text-amber-600 dark:text-amber-400',
    red: 'text-red-600 dark:text-red-400',
    teal: 'text-teal-600 dark:text-teal-400',
  };
  const strokeClasses = {
    green: 'stroke-emerald-500 dark:stroke-emerald-400',
    amber: 'stroke-amber-500 dark:stroke-amber-400',
    red: 'stroke-red-500 dark:stroke-red-400',
    teal: 'stroke-teal-500 dark:stroke-teal-400',
  };
  const size = 72;
  const strokeWidth = 6;
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const dashOffset = circumference - (arcPercent / 100) * circumference;

  return (
    <div className="flex flex-col items-center rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm dark:border-slate-700 dark:bg-slate-900/50">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-slate-200 dark:text-slate-700"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            className={strokeClasses[color]}
          />
        </svg>
        <div
          className="absolute left-0 top-0 flex h-full w-full items-center justify-center"
          style={{ width: size, height: size }}
        >
          <span className={`whitespace-nowrap font-bold text-lg leading-none ${colorClasses[color]}`}>{value}</span>
        </div>
      </div>
      {subLabel && (
        <span className="mt-1 text-muted-foreground text-xs">{subLabel}</span>
      )}
      <span className="font-medium text-foreground text-xs">{label}</span>
    </div>
  );
}

function ZoneCountsCard({
  counts,
  label,
  color,
}: {
  counts: Record<string, number>;
  label: string;
  color: 'green' | 'amber' | 'red' | 'teal';
}) {
  const colorClasses = {
    green: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
    red: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
    teal: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-200',
  };
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const zones = Object.entries(counts).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="flex flex-col rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm dark:border-slate-700 dark:bg-slate-900/50">
      <div className="flex items-center justify-center">
        <span className="font-bold text-foreground text-2xl">{total}</span>
      </div>
      <span className="mb-1.5 font-medium text-foreground text-xs">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {zones.map(([zone, count]) => (
          <span
            key={zone}
            className={`inline-flex rounded-full px-2 py-0.5 font-medium text-xs ${colorClasses[color]}`}
          >
            Zone {zone}: {count}
          </span>
        ))}
      </div>
    </div>
  );
}

export function MetricsOverview() {
  const { refreshKeys } = useTableRefresh();
  const metricsData = useTableData(`checkin_metrics`, refreshKeys[`checkin_metrics`] ?? 0);
  const flightsData = useTableData(`flights`, refreshKeys[`flights`] ?? 0);
  const agentsData = useTableData(`checkin_agents`, refreshKeys[`checkin_agents`] ?? 0);

  const loading = metricsData.loading || flightsData.loading || agentsData.loading;

  if (loading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white px-3 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-900/50">
        <h2 className="mb-2 font-medium text-foreground text-xs">Overview</h2>
        <p className="text-muted-foreground text-sm">Loading metrics...</p>
      </div>
    );
  }

  const metricsCols = metricsData.data?.columns ?? [];
  const flightsCols = flightsData.data?.columns ?? [];
  const agentsCols = agentsData.data?.columns ?? [];

  const avgColIdx = getColIndex(metricsCols, `avg_checkin_time_mins`);
  const zoneColIdx = getColIndex(metricsCols, `zone`);
  const delayRiskColIdx = getColIndex(flightsCols, `delay_risk`);
  const agentZoneColIdx = getColIndex(agentsCols, `zone`);
  const atCounterColIdx = getColIndex(agentsCols, `at_counter`);

  let maxAvgMins = 0;
  for (const row of metricsData.data?.rows ?? []) {
    const v = Number(getCell(row as unknown[], avgColIdx));
    if (!Number.isNaN(v) && v > maxAvgMins) maxAvgMins = v;
  }

  let atRiskCount = 0;
  for (const row of flightsData.data?.rows ?? []) {
    const v = String(getCell(row as unknown[], delayRiskColIdx)).toLowerCase();
    if (v === `at_risk`) atRiskCount++;
  }

  const activeByZone: Record<string, number> = {};
  const breakAwayByZone: Record<string, number> = {};
  for (const row of agentsData.data?.rows ?? []) {
    const zone = String(getCell(row as unknown[], agentZoneColIdx ?? -1)).trim();
    const status = String(getCell(row as unknown[], atCounterColIdx ?? -1)).toLowerCase();
    if (!zone) continue;
    if (status === `active`) {
      activeByZone[zone] = (activeByZone[zone] ?? 0) + 1;
    } else if (status === `break` || status === `away`) {
      breakAwayByZone[zone] = (breakAwayByZone[zone] ?? 0) + 1;
    }
  }

  const avgColor = avgCheckinColor(maxAvgMins);
  const avgArcPercent = Math.min(100, (maxAvgMins / 20) * 100);

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm dark:border-slate-700 dark:bg-slate-900/50">
      <h2 className="mb-2 font-medium text-foreground text-xs">Overview</h2>
      <div className="flex flex-wrap gap-3">
        <MetricCard
          value={maxAvgMins > 0 ? `${maxAvgMins.toFixed(1)} mn` : `—`}
          label="Av Checkin time"
          subLabel="worst zone"
          color={avgColor}
          arcPercent={avgArcPercent}
        />
        <MetricCard
          value={String(atRiskCount)}
          label="Flights at risk"
          subLabel="of flights"
          color={atRiskCount > 0 ? `red` : `teal`}
          arcPercent={atRiskCount > 0 ? 100 : 0}
        />
        <ZoneCountsCard
          counts={activeByZone}
          label="Active checkin agents"
          color="green"
        />
        <ZoneCountsCard
          counts={breakAwayByZone}
          label="Break or away agents"
          color="amber"
        />
      </div>
    </div>
  );
}
