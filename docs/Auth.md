# How to Replicate PAT-ONLY Authentication

If you already have the same `app` structure (e.g. from app-templates), no code changes are needed. Configure env vars and the existing code will use PAT.

---

## Setup (PAT – what is actually used)

Set in `.env.local` (or `.env`):

```
DATABRICKS_TOKEN=<your-personal-access-token>
DATABRICKS_HOST=https://<workspace>.azuredatabricks.net
```

With both set, **only PAT is used**. OAuth and CLI auth are not used.

---

## Why PAT is used (no changes needed)

The existing code already prefers PAT:

1. **Agent / chat API** (`packages/ai-sdk-providers/src/providers-server.ts`): If `DATABRICKS_TOKEN` is set, it returns it directly and never calls `getDatabricksToken()`.

2. **DB, SCIM, user session** (`packages/auth/src/databricks-auth.ts`): `getAuthMethod()` checks `shouldUseToken()` first. If both `DATABRICKS_TOKEN` and `DATABRICKS_HOST` are set, it returns `'token'` and never evaluates OAuth or CLI.

---

## Auth method priority (if PAT is not set)

1. **PAT** – `DATABRICKS_TOKEN` + `DATABRICKS_HOST`
2. **OAuth (service principal)** – `DATABRICKS_CLIENT_ID` + `DATABRICKS_CLIENT_SECRET` + `DATABRICKS_HOST`
3. **CLI (OAuth U2M)** – `DATABRICKS_CONFIG_PROFILE` or `DATABRICKS_HOST`; requires `databricks auth login`

---

## User session (who is logged in)

- **Production:** `X-Forwarded-User`, `X-Forwarded-Email`, `X-Forwarded-Preferred-Username` from Databricks Apps
- **Local dev:** SCIM API `/api/2.0/preview/scim/v2/Me` using the same token (PAT when `DATABRICKS_TOKEN` is set)
