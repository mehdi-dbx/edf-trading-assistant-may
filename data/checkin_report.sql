-- Check-in performance report: aggregates raw daily data by airline.
-- Expects raw data in a table or view named checkin_raw with columns:
--   date, airline, daily_check_ins, avg_time_min, load_factor_pct, sla_pct

SELECT
  airline AS "Airline",
  SUM(daily_check_ins) AS "Check-ins",
  ROUND(AVG(avg_time_min), 1) AS "Avg Time",
  ROUND(AVG(load_factor_pct), 0) AS "Load Factor",
  ROUND(AVG(sla_pct), 0) AS "SLA",
  CASE
    WHEN AVG(sla_pct) < 90 OR AVG(load_factor_pct) < 80 THEN 'Needs Attention'
    WHEN AVG(sla_pct) < 95 OR AVG(load_factor_pct) < 85 THEN 'Good'
    ELSE 'Excellent'
  END AS "Status"
FROM checkin_raw
GROUP BY airline
ORDER BY "Check-ins" DESC;
