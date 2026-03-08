CREATE OR REPLACE PROCEDURE mc.`amadeus-checkin`.update_flight_risk(
  IN flight_number_param STRING, 
  IN at_risk BOOLEAN
)
LANGUAGE SQL
SQL SECURITY INVOKER
AS 
BEGIN
  UPDATE mc.`amadeus-checkin`.flights
  SET delay_risk = CASE WHEN at_risk THEN 'AT_RISK' ELSE 'NONE' END
  WHERE mc.`amadeus-checkin`.flights.flight_number = flight_number_param;

  SELECT 'UPDATED' AS status;
END;


--CALL mc.`amadeus-checkin`.update_flight_risk('BA312', TRUE);
