DROP TABLE IF EXISTS mc.`amadeus-checkin`.border_terminals;

CREATE TABLE mc.`amadeus-checkin`.border_terminals (
    terminal_id STRING,
    zone STRING,
    priority STRING,
    status STRING
)
USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true);

INSERT INTO mc.`amadeus-checkin`.border_terminals VALUES
('eGate-C1', 'C', 'fast-track',   'OPERATIONAL'),
('eGate-C2', 'C', 'standard', 'OPERATIONAL'),
('eGate-C3', 'C', 'standard',   'OUT OF SERVICE');