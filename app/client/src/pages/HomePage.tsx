import { useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { useTableRefresh } from '@/contexts/TableRefreshContext';
import { useTableData, getRowKey } from '@/hooks/useTableData';

const TIMESTAMP_COLUMNS = ['recorded_at', 'last_checked', 'departure_time', 'scheduled_date', 'event_timestamp', 'updated_at'];

const TABLE_PASTELS: Record<string, string> = {
  example_data: 'bg-slate-100 dark:bg-slate-900/30',
};

function displayName(name: string): string {
  return name.replace(/_/g, ' ');
}

function formatCell(cell: unknown, columnName: string): string {
  if (cell == null) return '—';
  const s = String(cell);
  const col = columnName.toLowerCase();
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

function TableCard({ title, tableName, compact, id }: { title: string; tableName: string; compact?: boolean; id?: string }) {
  const { refreshKeys, refresh } = useTableRefresh();
  const refreshTrigger = refreshKeys[tableName] ?? 0;
  const { data, loading, error, changedRowKeys, setChangedRowKeys } = useTableData(tableName, refreshTrigger);

  useEffect(() => {
    if (changedRowKeys.size > 0) {
      const t = setTimeout(() => setChangedRowKeys(new Set()), 2000);
      return () => clearTimeout(t);
    }
  }, [changedRowKeys.size, setChangedRowKeys]);

  return (
    <div id={id} className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900/50">
      <div
        className={[
          'flex items-center justify-between border-b border-slate-200 px-3 py-1.5 dark:border-slate-700',
          TABLE_PASTELS[tableName] ?? 'bg-slate-50 dark:bg-slate-800/50',
        ].join(' ')}
      >
        <h2 className="font-medium text-foreground text-xs">{displayName(title)}</h2>
        <button
          type="button"
          onClick={() => refresh(tableName)}
          disabled={loading}
          aria-label="Refresh"
          className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
        >
          <RefreshCw
            className={`size-3.5 ${loading ? 'animate-spin' : ''}`}
          />
        </button>
      </div>
      <div className="overflow-x-auto p-[10px]">
        {error && (
          <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
        )}
        {!data && loading && (
          <p className="text-xs text-muted-foreground">Loading...</p>
        )}
        {data && (
          <table className={`w-full border-collapse text-xs ${compact ? 'min-w-[200px]' : 'min-w-[360px]'}`}>
            <thead>
              <tr>
                {data.columns.map((col) => (
                  <th
                    key={col}
                    className="border-b border-slate-200 px-2.5 py-1.5 text-left font-medium text-foreground dark:border-slate-700"
                  >
                    {displayName(col)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={data.columns.length}
                    className="px-2.5 py-2 text-center text-muted-foreground"
                  >
                    No rows
                  </td>
                </tr>
              ) : (
                data.rows.map((row, i) => {
                  const rowKey = getRowKey(row, data.columns, tableName);
                  const isChanged = changedRowKeys.has(rowKey);
                  return (
                  <tr
                    key={i}
                    className={[
                      'border-b border-slate-100 dark:border-slate-800',
                      isChanged ? 'animate-row-flash' : '',
                    ].filter(Boolean).join(' ')}
                  >
                    {row.map((cell, j) => {
                      const col = data.columns[j] ?? '';
                      const display = formatCell(cell, col);
                      return (
                        <td
                          key={j}
                          className="px-2.5 py-1.5 text-muted-foreground"
                        >
                          {display}
                        </td>
                      );
                    })}
                  </tr>
                  );
                })
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
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-auto px-4 py-3">
      <h1 className="mb-2 font-medium text-foreground text-sm">Dashboard</h1>
      <div className="flex flex-col gap-3">
        <TableCard id="example-data-table" title="example_data" tableName="example_data" />
      </div>
    </div>
  );
}
