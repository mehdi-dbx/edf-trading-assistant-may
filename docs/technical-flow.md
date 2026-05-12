# Technical Flow – TUNRAROUND Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  USER                                                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (Vite 3000)                                                                       │
│  • sendMessage → POST /api/chat                                                             │
│  • parseResponseBlocks → RefreshTableTrigger, FollowUpActions, Cards                        │
│  • useTableData → GET /api/tables/:id                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ├──────────────────────────────────┬──────────────────────────────────┐
        ▼                                  ▼                                  ▼
┌─────────────────────┐    ┌─────────────────────────────────┐    ┌─────────────────────────────┐
│  Node (Express 3001)│    │  Node /api/chat                 │    │  Node /api/tables/:id       │
│  POST /api/chat     │    │  → API_PROXY (8000/invocations) │    │  → Databricks SQL API       │
│  POST /api/reset    │    │  → stream SSE to client         │    │  → SELECT * (or latest/zone)│
│                    │    └─────────────────────────────────┘    └─────────────────────────────┘
│                    │    GET /api/events/tasks (SSE)              │
│  POST /api/events/  │    POST /api/events/task-created            │
│    task-created     │    (staffing duty notifications)           │
└─────────────────────┘                      │                                    │
        │                                    ▼                                    │
        │                    ┌───────────────────────────────────────────────────┐│
        │                    │  Backend (FastAPI 8000)                           ││
        │                    │  POST /invocations → AgentServer                  ││
        │                    │                                                    ││
        │                    └───────────────────────────────────────────────────┘│
        │                                    │                                    │
        │                                    ▼                                    │
        │                    ┌───────────────────────────────────────────────────┐│
        │                    │  AGENT (LangChain, prompt/main.prompt)            ││
        │                    │  Tools: create_*_incident,                         ││
        │                    │  back_to_normal, update_checkin_agent,            ││
        │                    │  update_border_officer, update_flight_risk,       │
        │                    │  confirm_arrival                                  ││
        │                    │  MCP: Genie (AMADEUS_GENIE_CHECKIN)               ││
        │                    └───────────────────────────────────────────────────┘│
        │                                   │                                     │
        │              ┌────────────────────┼────────────────────┐                │
        │              ▼                    ▼                                     │
        │    ┌─────────────────┐  ┌─────────────────┐                            │
        │    │ sql_executor    │  │ Genie MCP       │                            │
        │    │ → statement_    │  │ → Genie Space   │                            │
        │    │   execution API │  │   (NL → SQL)    │                            │
        │    └────────┬────────┘  └────────┬────────┘                            │
        │             │                    │                                      │
        ▼             ▼                    ▼                                      │
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  DATABRICKS                                                                                 │
│  • SQL Warehouse: statement_execution (tools, procedures, tables API)                       │
│  • Unity Catalog: mc.amadeus-checkin (checkin_metrics, flights, checkin_agents,             │
│    border_officers, border_terminals)                                                       │
│  • Genie Space: AMADEUS_GENIE_CHECKIN (NL queries over UC tables)                           │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Key Files

| Path | Purpose |
|------|---------|
| prompt/main.prompt | Agent instructions, Genie query templates, block formats |
| agent_server/agent.py | Agent init, tools, MCP client |
| agent_server/start_server.py | FastAPI app |
| tools/sql_executor.py | Databricks statement_execution |
| tools/create_checkin_incident.py | Zone B anomaly |
| tools/create_border_incident.py | Zone C anomaly |
| tools/back_to_normal.py | Restore zone baseline |
| tools/update_checkin_agent.py | CALL update_checkin_agent (+ POST task-created when assigned_by_id) |
| tools/update_border_officer.py | CALL update_border_officer |
| tools/confirm_arrival.py | CALL confirm_arrival |
| tools/update_flight_risk.py | CALL update_flight_risk |
| data/init/create_*.sql | Table DDL + seed data |
| data/proc/*_procedure.sql | Stored procedures |
| data/confirm_arrival_procedure.sql | confirm_arrival procedure |
| data/create_genie_space.py | Create Genie space, set AMADEUS_GENIE_CHECKIN |
| scripts/reset_state.py | Re-run create SQL scripts |
| app/server/src/routes/tables.ts | GET /api/tables → Databricks SQL |
| app/server/src/routes/chat.ts | POST /api/chat → agent |
| app/client/src/lib/response-blocks.ts | Parse blocks from agent text |
