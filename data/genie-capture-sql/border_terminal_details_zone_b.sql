-- Border terminals in Zone B: lists each terminal with status plus a total row per status showing count.
SELECT `terminal_id`, `status`, NULL AS `terminal_count` FROM __SCHEMA_QUALIFIED__.`border_terminals` WHERE `zone` = 'B' UNION ALL SELECT 'TOTAL' AS `terminal_id`, `status`, COUNT(*) AS `terminal_count` FROM __SCHEMA_QUALIFIED__.`border_terminals` WHERE `zone` = 'B' GROUP BY `status`
