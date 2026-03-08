-- Staffing duties: rows from checkin_agents where agent has NEW staffing_status. Params: {agent_id}
SELECT zone, counter, assigned_by_id, assigned_at FROM `mc`.`amadeus-checkin`.`checkin_agents` WHERE agent_id = '{agent_id}' AND staffing_status = 'NEW'
