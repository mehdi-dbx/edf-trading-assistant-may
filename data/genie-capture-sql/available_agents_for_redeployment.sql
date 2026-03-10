-- Available agents for redeployment: lists check-in agents currently on break or available (not at counter).
SELECT `agent_id`, `name`, `zone`, `counter`, `at_counter` FROM __SCHEMA_QUALIFIED__.`checkin_agents` WHERE `at_counter` IN ('BREAK', 'AVAILABLE') AND `agent_id` IS NOT NULL AND `name` IS NOT NULL AND `zone` IS NOT NULL AND `counter` IS NOT NULL AND `at_counter` IS NOT NULL
