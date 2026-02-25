import { useEffect, useState } from 'react';

export type TableData = {
  columns: string[];
  rows: unknown[][];
} | null;

export type TableState = {
  data: TableData;
  loading: boolean;
  error: string | null;
};

export function useTableData(
  tableName: string,
  refreshTrigger: number,
): TableState {
  const [data, setData] = useState<TableData>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
  }, [tableName, refreshTrigger]);

  return { data, loading, error };
}
