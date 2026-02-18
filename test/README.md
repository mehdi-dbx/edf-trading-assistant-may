# Test scripts

Scripts to exercise the agent from the command line (e.g. to monitor chat responses).

## Prerequisites

Start the app so the agent backend is running:

```bash
./scripts/start_local.sh
```

This brings up the backend on port 8000 (and the Node app on 3001, frontend on 3000).

## Send "hello" to the agent

From the **project root**:

```bash
python test/send_hello_to_agent.py
```

Or from the **test** folder:

```bash
cd test && python send_hello_to_agent.py
```

The script:

- POSTs a single user message `"hello"` to the agent’s `/invocations` endpoint
- Prints the request URL, body, and full response (parsed JSON or raw)
- Prints HTTP status and elapsed time so you can monitor the response closely

## Overriding the agent URL

By default the script uses `http://localhost:8000/invocations`. You can override:

- `AGENT_URL` – full URL (e.g. `AGENT_URL=https://my-agent.example/invocations python test/send_hello_to_agent.py`)
- Or `AGENT_HOST` and `AGENT_PORT` (e.g. `AGENT_PORT=9000 python test/send_hello_to_agent.py`)
