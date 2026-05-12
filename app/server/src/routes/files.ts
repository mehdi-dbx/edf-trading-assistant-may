import { Router, type Request, type Response } from 'express';
import { authMiddleware } from '../middleware/auth';

export const filesRouter = Router();
filesRouter.use(authMiddleware);

/**
 * GET /api/files?path=/Volumes/...
 * Proxy to Python backend /files?path=... which has Databricks auth.
 * Streams the response so large files (PDFs, TXTs) are not buffered in Node.
 */
filesRouter.get('/', async (req: Request, res: Response) => {
  const path = typeof req.query.path === 'string' ? req.query.path : '';
  if (!path.startsWith('/Volumes/')) {
    return res.status(400).json({ error: 'path must start with /Volumes/' });
  }

  const apiProxy = process.env.API_PROXY || '';
  let base = apiProxy.replace(/\/invocations\/?$/, '') || 'http://127.0.0.1:8000';
  if (base.startsWith('http://localhost:') || base.startsWith('https://localhost:')) {
    base = base.replace('localhost', '127.0.0.1');
  }
  const url = `${base}/files?path=${encodeURIComponent(path)}`;

  try {
    const upstream = await fetch(url);
    if (!upstream.ok) {
      const text = await upstream.text();
      console.error('[files] backend error', upstream.status, text.slice(0, 200));
      return res.status(upstream.status).json({ error: 'Backend files error', details: text.slice(0, 200) });
    }
    const contentType = upstream.headers.get('content-type') ?? 'application/octet-stream';
    res.setHeader('Content-Type', contentType);
    res.setHeader('Content-Disposition', 'inline');
    if (upstream.body) {
      const reader = upstream.body.getReader();
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          res.write(value);
        }
      } finally {
        reader.releaseLock();
      }
    }
    res.end();
  } catch (err) {
    console.error('[files] fetch error', url, err);
    return res.status(502).json({
      error: 'Backend unavailable',
      message: err instanceof Error ? err.message : 'Unknown error',
    });
  }
});
