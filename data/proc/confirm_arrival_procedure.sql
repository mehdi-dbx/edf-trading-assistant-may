CREATE OR REPLACE PROCEDURE mc.`amadeus-checkin`.confirm_arrival(
  IN agent_id_param STRING
)
LANGUAGE SQL
SQL SECURITY INVOKER
AS 
BEGIN
  UPDATE mc.`amadeus-checkin`.checkin_agents
  SET staffing_status = 'COMPLETED'
  WHERE agent_id = agent_id_param AND staffing_status = 'NEW';
  SELECT 'UPDATED' AS status;
END;
