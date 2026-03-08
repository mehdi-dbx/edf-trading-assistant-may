-- E-gate availability: counts how many terminals are operational vs out of service. Params: {zone}
SELECT `status`, COUNT(*) AS num_terminals, COLLECT_LIST(`terminal_id`) AS terminal_ids FROM `mc`.`amadeus-checkin`.`border_terminals` WHERE `zone` ILIKE '{zone_pattern}' AND `status` IN ('OPERATIONAL', 'OUT OF SERVICE') GROUP BY `status`
