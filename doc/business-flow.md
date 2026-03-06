# Amadeus Check-in Ops – Business Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AMADEUS CHECK-IN OPS FLOW                        │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────┐         ┌──────────────────┐
  │ Check-in         │         │ Border Control   │
  │ Performance      │         │ Performance      │
  └────────┬─────────┘         └────────┬─────────┘
           │                            │
           ▼                            ▼
  ┌─────────────────────────────────────────────────┐
  │  create_checkin_incident (Zone B)               │
  │  create_border_incident (Zone C)                │
  │  → refresh checkin_metrics                      │
  └────────────────────┬────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────┐
  │  Identify at-risk flights (Genie)               │
  │  → update_flight_risk                           │
  └────────────────────┬────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────┐
  │  Root cause analysis (Genie)                    │
  │  • Staffing / border officers / e-Gates         │
  │  → Recommended action                           │
  └────────────────────┬────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
  ┌─────────────────┐     ┌─────────────────┐
  │ Deploy check-in │     │ Pull border     │
  │ agent           │     │ officer off     │
  │ update_checkin_ │     │ break           │
  │ agent           │     │ update_border_  │
  │                 │     │ officer         │
  └────────┬────────┘     └────────┬────────┘
           │                       │
           └───────────┬───────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────┐
  │  Zone back to normal                            │
  │  back_to_normal → update_flight_risk (NORMAL)   │
  └─────────────────────────────────────────────────┘
```
