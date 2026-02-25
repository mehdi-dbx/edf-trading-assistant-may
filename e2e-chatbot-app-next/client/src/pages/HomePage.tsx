import { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';

const TIMESTAMP_COLUMNS = ['recorded_at', 'last_checked', 'departure_time', 'scheduled_date', 'event_timestamp'];

const TABLE_PASTELS: Record<string, string> = {
  checkin_metrics: 'bg-rose-100 dark:bg-rose-900/30',
  flights: 'bg-sky-100 dark:bg-sky-900/30',
  checkin_agents: 'bg-emerald-100 dark:bg-emerald-900/30',
};

function atCounterCapsuleClass(value: string): string {
  const v = value.toLowerCase();
  if (v === 'active') return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200';
  if (v === 'away') return 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200';
  if (v === 'break') return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200';
  if (v === 'available') return 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200';
  return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
}

function formatCell(cell: unknown, columnName: string): string {
  if (cell == null) return '—';
  const s = String(cell);
  if (columnName.toLowerCase() === 'at_counter') return s.toLowerCase();
  const isTimestampColumn = TIMESTAMP_COLUMNS.some((c) =>
    columnName.toLowerCase().includes(c.toLowerCase()),
  );
  const looksLikeTimestamp =
    /^\d{4}-\d{2}-\d{2}(T|\s)\d{2}:\d{2}/.test(s) || /^\d{4}-\d{2}-\d{2}$/.test(s);
  if ((isTimestampColumn || looksLikeTimestamp) && s) {
    try {
      const d = new Date(s);
      if (!Number.isNaN(d.getTime())) {
        return d.toLocaleString(undefined, {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
        }).replace(/,/g, '');
      }
    } catch {
      /* fall through */
    }
  }
  return s;
}

type TableData = {
  columns: string[];
  rows: unknown[][];
} | null;

type TableState = {
  data: TableData;
  loading: boolean;
  error: string | null;
};

function useTableData(tableName: string): TableState & { refetch: () => void } {
  const [data, setData] = useState<TableData>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/tables/${tableName}`, { credentials: 'include' })
      .then(async (res) => {
        const text = await res.text();
        let body: { error?: string; message?: string };
        try {
          body = text ? JSON.parse(text) : {};
        } catch {
          throw new Error(res.ok ? 'Invalid response from server' : `HTTP ${res.status}: ${text.slice(0, 100)}`);
        }
        if (!res.ok) {
          throw new Error(body.error ?? body.message ?? `HTTP ${res.status}`);
        }
        return body as { columns: string[]; rows: unknown[][] };
      })
      .then((body: { columns: string[]; rows: unknown[][] }) => {
        if (!cancelled) {
          setData({ columns: body.columns, rows: body.rows });
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tableName, refresh]);

  return { data, loading, error, refetch: () => setRefresh((r) => r + 1) };
}

function TableCard({ title, tableName }: { title: string; tableName: string }) {
  const { data, loading, error, refetch } = useTableData(tableName);

  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900/50">
      <div
        className={[
          'flex items-center justify-between border-b border-slate-200 px-3 py-2 dark:border-slate-700',
          TABLE_PASTELS[tableName] ?? 'bg-slate-50 dark:bg-slate-800/50',
        ].join(' ')}
      >
        <h2 className="font-medium text-foreground text-xs">{title}</h2>
        <button
          type="button"
          onClick={refetch}
          disabled={loading}
          aria-label="Refresh"
          className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
        >
          <RefreshCw
            className={`size-3.5 ${loading ? 'animate-spin' : ''}`}
          />
        </button>
      </div>
      <div className="overflow-x-auto p-3">
        {error && (
          <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
        )}
        {!error && loading && (
          <p className="text-xs text-muted-foreground">Loading...</p>
        )}
        {!error && !loading && data && (
          <table className="w-full min-w-[360px] border-collapse text-xs">
            <thead>
              <tr>
                {data.columns.map((col) => (
                  <th
                    key={col}
                    className="border-b border-slate-200 px-2.5 py-1.5 text-left font-medium text-foreground dark:border-slate-700"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={data.columns.length}
                    className="px-2.5 py-3 text-center text-muted-foreground"
                  >
                    No rows
                  </td>
                </tr>
              ) : (
                data.rows.map((row, i) => (
                  <tr
                    key={i}
                    className="border-b border-slate-100 dark:border-slate-800"
                  >
                    {row.map((cell, j) => {
                      const col = data.columns[j] ?? '';
                      const colLower = col.toLowerCase();
                      const display = formatCell(cell, col);
                      const isAgentId = colLower === 'agent_id';
                      const isAtCounter = colLower === 'at_counter';
                      const isCapsule = isAgentId || isAtCounter;
                      return (
                        <td
                          key={j}
                          className="px-2.5 py-1.5 text-muted-foreground"
                        >
                          {isCapsule ? (
                            <span
                              className={[
                                'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                                isAgentId
                                  ? 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                                  : atCounterCapsuleClass(display),
                              ].join(' ')}
                            >
                              {display}
                            </span>
                          ) : (
                            display
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-auto p-4">
      <h1 className="mb-3 font-medium text-foreground text-sm">Dashboard</h1>
      <div className="flex flex-col gap-4">
        <TableCard title="checkin_metrics" tableName="checkin_metrics" />
        <TableCard title="flights" tableName="flights" />
        <TableCard title="checkin_agents" tableName="checkin_agents" />
      </div>
    </div>
  );
}
