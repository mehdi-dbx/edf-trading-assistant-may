DROP TABLE IF EXISTS mc.`amadeus-checkin`.checkin_metrics;

CREATE TABLE mc.`amadeus-checkin`.checkin_metrics (
    zone STRING,
    avg_checkin_time_mins DOUBLE,
    baseline_mins DOUBLE,
    pct_change DOUBLE,
    window_mins INT,
    recorded_at TIMESTAMP_NTZ
)
USING DELTA;
