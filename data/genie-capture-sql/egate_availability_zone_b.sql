-- E-gate availability in Zone B: counts how many terminals are operational vs out of service.
SELECT `status`, COUNT(*) AS num_terminals, COLLECT_LIST(`terminal_id`) AS terminal_ids FROM `mc`.`amadeus-checkin`.`border_terminals` WHERE `zone` ILIKE '%B%' AND `status` IN ('OPERATIONAL', 'OUT OF SERVICE') GROUP BY `status`
