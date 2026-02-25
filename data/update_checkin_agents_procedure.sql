CREATE OR REPLACE PROCEDURE mc.`amadeus-checkin`.update_checkin_agent(
  IN agent_id_param STRING,
  IN zone_param STRING,
  IN counter_param STRING,
  IN at_counter_param STRING
)
LANGUAGE SQL
SQL SECURITY INVOKER
AS 
BEGIN
  UPDATE mc.`amadeus-checkin`.checkin_agents
  SET zone = zone_param, counter = counter_param, at_counter = at_counter_param
  WHERE agent_id = agent_id_param;

  SELECT 'UPDATED' AS status;
END;


--CALL mc.`amadeus-checkin`.update_checkin_agent('A14', 'B', 'B08', 'ACTIVE');
