-- Check-in agents grouped by counter status: counts per status (ACTIVE, BREAK, etc.) and lists agent IDs/names. Params: {zone}
SELECT `at_counter`, COUNT(*) AS agent_count, COLLECT_LIST(`agent_id`) AS agent_ids, COLLECT_LIST(`name`) AS agent_names
FROM `mc`.`amadeus-checkin`.`checkin_agents`
WHERE `zone` = '{zone}' AND `at_counter` IS NOT NULL
GROUP BY `at_counter`
ORDER BY agent_count DESC;
