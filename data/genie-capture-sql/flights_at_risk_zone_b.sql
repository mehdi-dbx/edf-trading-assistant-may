-- Flights at risk of delay: flights checking in through Zone B departing within the next 60 minutes.
SELECT `flight_number`, `departure_time` FROM __SCHEMA_QUALIFIED__.`flights` WHERE `zone` = 'B' AND `departure_time` >= TIMESTAMP('2026-02-25 10:05:00') AND `departure_time` < TIMESTAMP('2026-02-25 11:05:00') AND `flight_number` IS NOT NULL AND `departure_time` IS NOT NULL AND `zone` IS NOT NULL;
