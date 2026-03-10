CREATE OR REPLACE PROCEDURE __SCHEMA_QUALIFIED__.update_flight_risk(
  IN flight_number_param STRING, 
  IN at_risk BOOLEAN
)
LANGUAGE SQL
SQL SECURITY INVOKER
AS 
BEGIN
  UPDATE __SCHEMA_QUALIFIED__.flights
  SET delay_risk = CASE WHEN at_risk THEN 'AT_RISK' ELSE 'NONE' END
  WHERE __SCHEMA_QUALIFIED__.flights.flight_number = flight_number_param;

  SELECT 'UPDATED' AS status;
END;


--CALL __SCHEMA_QUALIFIED__.update_flight_risk('BA312', TRUE);
