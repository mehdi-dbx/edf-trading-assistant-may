# Startup: What Went Wrong and How It Was Fixed

Short summary of local startup issues and fixes.

## Problem: "Unable to connect" at http://localhost:3000

**What went wrong:** Firefox showed "Unable to connect" because nothing was listening on port 3000. Either no dev script was running, or the script had exited.

**Fix:** Run the full stack with `./scripts/start_local.sh`. It starts backend (8000), Node API (3001), and Vite frontend (3000). Port cleanup at start kills any process already on 8000, 3000, or 3001 so a previous run doesn’t block.

---

## Problem: Two dev scripts (dev.sh vs dev-with-auth.sh)

**What went wrong:** `dev.sh` only ran backend + Vite (no Node server). So `/api/session` and chat had nowhere to go → "Authentication Required" and broken app. Having two scripts was confusing.

**Fix:** Single local script: `./scripts/start_local.sh`. It always runs the full stack (backend + Node + Vite). The incomplete `dev.sh` and `dev-with-auth.sh` were removed. Deploy still uses `uv run start-app` (build + serve).

---

## Problem: Node server failed with EPERM (tsx pipe)

**What went wrong:** When the stack was started from the IDE/background, the Node server (`npm run dev:server`) failed with:
`Error: listen EPERM: operation not permitted /var/folders/.../tsx-....pipe`.  
`tsx watch` creates an IPC pipe; in that environment the process wasn’t allowed to create it.

**Fix:** Use the **built** Node server instead of `tsx watch`. The script builds the server if needed (`npm run build:server`) and runs `npm run dev:built` (runs `node dist/index.mjs`). No tsx, no pipe, so no EPERM. The server package has a `dev:built` script for this.

---

## Problem: Vite failed with EPERM (bind to port)

**What went wrong:** Vite failed with:
`Error: listen EPERM: operation not permitted ::1:3000` (or `127.0.0.1:3000`).  
In the same restricted/background environment, binding to a port was not allowed.

**Fix:**  
1. **Vite config:** Set `server.host: '127.0.0.1'` in `app/client/vite.config.ts` so Vite binds to IPv4 only (avoids IPv6 issues where relevant).  
2. **Environment:** Starting the stack from a normal terminal (e.g. Terminal.app or the IDE terminal) avoids the restriction. Running `./scripts/start_local.sh` from the IDE with **full permissions** also allows port binding so the app can start from the IDE.

---

## Problem: start_local.sh exited because one process died

**What went wrong:** The script starts three processes (backend, Node, Vite). When one failed (e.g. Node or Vite with EPERM), the script’s monitor loop saw a dead PID and exited, killing the rest.

**Fix:** Fix the underlying failures (built Node server, Vite host, permissions). The script uses subshells and PID files so it tracks the real process PIDs (not the wrapper) and keeps running as long as all three are alive.

---

## Current layout

| What              | Command / file                          | Purpose                                      |
|-------------------|------------------------------------------|----------------------------------------------|
| Local full stack  | `./scripts/start_local.sh`              | Backend (8000) + Node (3001) + Vite (3000)   |
| Deploy / build    | `uv run start-app`                      | Clone frontend, build, run backend + static  |
| Port cleanup      | Inside `start_local.sh`                 | Kills 8000, 3000, 3001 at start              |
| Node dev          | `dev:built` in server package            | Run built server (no tsx) when needed        |

Open **http://localhost:3000** after `./scripts/start_local.sh` is running.
