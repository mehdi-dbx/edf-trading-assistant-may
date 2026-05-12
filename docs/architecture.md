# EDF Trading Assistant — Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     EDF TRADING ASSISTANT (Agent)                            │
│                     LangGraph + Claude Sonnet 4.6                             │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐       ┌───────────────┐
│  KAs (15)     │       │  GENIE        │
│  Document Q&A │       │  EDF TRADING  │
└───────────────┘       │  SQL / tables │
        │               └───────────────┘
        │                       │
        ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  KA TOOLS (Knowledge Assistants)                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  • nao-north-atlantic-oscillation-trading-data                                │
│  • epo-east-pacific-oscillation-trading-assistant                              │
│  • daily_outlook_2020_2025                                                    │
│  • mjo-phase-energy-trading-assistant                                         │
│  • daily_outlook_2015_2019                                                    │
│  • degree-days-energy-trading-assistant                                       │
│  • daily_outlook_2005_2009                                                    │
│  • cwg-wind-generation-forecasts                                             │
│  • climate-teleconnections-learnings                                          │
│  • wpo-west-pacific-oscillation-trading-data                                  │
│  • mjo-madden-julian-oscillation-agent                                       │
│  • global-tropics-hazards-cpc-briefings                                       │
│  • ENSO-Climate-Trading-Assistant                                             │
│  • pna-teleconnection-trading-assistant                                       │
│  • CPC-Daily-Outlook-Energy-Trading                                           │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│  GENIE TOOL — Tables (edf.chatbot)                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│  • bronze_degree_days_forecast    • bronze_degree_days_historical             │
│  • bronze_degree_days_normals     • epo_forecast_bronze                       │
│  • epo_historical_bronze         • bronze_mjo_phase_forecast                 │
│  • bronze_mjo_phase_historical    • nao_forecast_bronze                       │
│  • nao_historical_bronze         • pna_forecast_bronze                        │
│  • pna_historical_bronze         • bronze_wpo_forecast                       │
│  • bronze_wpo_historical                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```
