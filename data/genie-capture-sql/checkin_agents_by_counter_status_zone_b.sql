-- Check-in agents in Zone B grouped by counter status: counts per status (ACTIVE, BREAK, etc.) and lists agent IDs/names.
SELECT `at_counter`, COUNT(*) AS agent_count, COLLECT_LIST(`agent_id`) AS agent_ids, COLLECT_LIST(`name`) AS agent_names
FROM __SCHEMA_QUALIFIED__.`checkin_agents`
WHERE `zone` ILIKE 'B' AND `at_counter` IS NOT NULL
GROUP BY `at_counter`
ORDER BY agent_count DESC;
