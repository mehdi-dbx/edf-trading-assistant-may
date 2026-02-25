import { Router, type Request, type Response } from 'express';
import { authMiddleware, requireAuth } from '../middleware/auth';

const ALLOWED_TABLES = ['checkin_metrics', 'flights', 'checkin_agents'] as const;

export const tablesRouter = Router();
tablesRouter.use(authMiddleware);

/**
 * GET /api/tables/:tableName - Fetch table data from Databricks Delta
 * Returns { columns: string[], rows: any[][] }
 */
tablesRouter.get('/:tableName', requireAuth, async (req: Request, res: Response) => {
  const tableName = req.params.tableName;
  if (!ALLOWED_TABLES.includes(tableName as (typeof ALLOWED_TABLES)[number])) {
    return res.status(400).json({ error: 'Table not allowed', allowed: [...ALLOWED_TABLES] });
  }

  const host = process.env.DATABRICKS_HOST;
  const token = process.env.DATABRICKS_TOKEN;
  const warehouseId = process.env.DATABRICKS_WAREHOUSE_ID;
  const schemaSpec = process.env.AMADEUS_UNITY_CATALOG_SCHEMA;

  if (!host || !token || !warehouseId || !schemaSpec || !schemaSpec.includes('.')) {
    return res.status(502).json({
      error: 'Databricks not configured',
      message: 'Missing DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID, or AMADEUS_UNITY_CATALOG_SCHEMA',
    });
  }

  const [catalog, schema] = schemaSpec.trim().split('.', 2);
  const fullTable = schema.includes('-') || schema.includes(' ')
    ? `${catalog}.\`${schema}\`.${tableName}`
    : `${catalog}.${schema}.${tableName}`;
  const statement = `SELECT * FROM ${fullTable}`;

  const url = `${host.replace(/\/$/, '')}/api/2.0/sql/statements`;
  try {
    const execRes = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        warehouse_id: warehouseId,
        statement,
        wait_timeout: '30s',
        format: 'JSON_ARRAY',
      }),
    });

    const respText = await execRes.text();
    if (!execRes.ok) {
      console.error('[tables] Databricks API error', execRes.status, respText.slice(0, 300));
      return res.status(502).json({
        error: 'Databricks unavailable',
        details: respText.slice(0, 200),
      });
    }

    let data: {
      status?: { state?: string; error?: { message?: string } };
      manifest?: { schema?: { columns?: Array<{ name?: string }> } };
      result?: { data_array?: unknown[][] };
      statement_id?: string;
    };
    try {
      data = JSON.parse(respText) as typeof data;
    } catch (parseErr) {
      console.error('[tables] Databricks response not JSON', respText.slice(0, 200));
      return res.status(502).json({
        error: 'Databricks returned invalid response',
        details: respText.slice(0, 200),
      });
    }

    const state = data.status?.state;
    if (state === 'FAILED' || state === 'CANCELED') {
      const msg = data.status?.error?.message ?? state;
      return res.status(502).json({ error: 'Query failed', details: msg });
    }

    if (state !== 'SUCCEEDED' && state !== 'CLOSED') {
      return res.status(502).json({
        error: 'Query did not complete',
        state,
        message: 'Statement may still be running. Try again.',
      });
    }

    const columns =
      data.manifest?.schema?.columns?.map((c) => c.name ?? '') ?? [];
    const rows = (data.result?.data_array ?? []) as unknown[][];

    return res.json({ columns, rows });
  } catch (err) {
    console.error('[tables] fetch error', err);
    return res.status(502).json({
      error: 'Databricks unavailable',
      message: err instanceof Error ? err.message : 'Unknown error',
    });
  }
});
