-- Border officers grouped by post status: counts officers per status and lists officer_id/name. Params: {zone}
SELECT `at_post` AS status, COUNT(*) AS officer_count, COLLECT_LIST(NAMED_STRUCT('officer_id', `officer_id`, 'name', `name`)) AS officers FROM `mc`.`amadeus-checkin`.`border_officers` WHERE `zone` = '{zone}' GROUP BY `at_post`
