DROP TABLE IF EXISTS mc.`amadeus-checkin`.border_officers;

CREATE TABLE mc.`amadeus-checkin`.border_officers (
    officer_id STRING,
    name STRING,
    zone STRING,
    at_post STRING
)
USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true);

INSERT INTO mc.`amadeus-checkin`.border_officers VALUES
('O01', 'J. Martinez', 'C', 'ACTIVE'),
('O02', 'P. Kowalski', 'C', 'ACTIVE'),
('O03', 'A. Chen', 'C', 'BREAK');
