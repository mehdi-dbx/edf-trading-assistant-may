-- Check-in performance metrics: latest avg check-in time, baseline, % change vs baseline, and anomaly flag per zone. Params: {zone} (optional, omit for all zones)
WITH latest_metrics AS (
  SELECT 
    zone, 
    MAX(recorded_at) AS latest_recorded_at
  FROM __SCHEMA_QUALIFIED__.`checkin_metrics`
  WHERE zone IS NOT NULL AND recorded_at IS NOT NULL {zone_filter}
  GROUP BY zone
)
SELECT 
  m.zone, 
  m.avg_checkin_time_mins AS avg_checkin_time, 
  m.baseline_mins AS baseline, 
  m.pct_change, 
  m.window_mins, 
  m.recorded_at AS timestamp,
  CASE WHEN ABS(m.pct_change) > 0.2 THEN TRUE ELSE FALSE END AS is_anomalous
FROM __SCHEMA_QUALIFIED__.`checkin_metrics` m
JOIN latest_metrics lm
  ON m.zone = lm.zone AND m.recorded_at = lm.latest_recorded_at
ORDER BY m.zone
