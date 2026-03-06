DROP TABLE IF EXISTS mc.`amadeus-checkin`.flights;

CREATE TABLE mc.`amadeus-checkin`.flights (
    flight_number STRING,
    zone STRING,
    departure_time TIMESTAMP_NTZ,
    delay_risk STRING,
    status STRING
)
USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true);

INSERT INTO mc.`amadeus-checkin`.flights VALUES
('BA312', 'B', CAST('2026-02-25 10:30:00' AS TIMESTAMP_NTZ), 'NONE', 'ON STAND'),
('BA418', 'B', CAST('2026-02-25 10:30:00' AS TIMESTAMP_NTZ), 'NONE', 'ON STAND'),
('AF134', 'C', CAST('2026-02-25 10:40:00' AS TIMESTAMP_NTZ), 'NONE', 'ON STAND'),
('AF178', 'C', CAST('2026-02-25 10:40:00' AS TIMESTAMP_NTZ), 'NONE', 'ON STAND');
