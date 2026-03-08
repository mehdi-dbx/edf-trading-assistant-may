CREATE OR REPLACE PROCEDURE mc.`amadeus-checkin`.update_border_officer(
  IN officer_id_param STRING,
  IN at_post_param STRING
)
LANGUAGE SQL
SQL SECURITY INVOKER
AS 
BEGIN
  UPDATE mc.`amadeus-checkin`.border_officers
  SET at_post = at_post_param
  WHERE officer_id = officer_id_param;

  SELECT 'UPDATED' AS status;
END;


--CALL mc.`amadeus-checkin`.update_border_officer('O03', 'ACTIVE');
