-- Border officers in Zone B grouped by post status: counts officers per status and lists officer_id/name.
SELECT `at_post` AS status, COUNT(*) AS officer_count, COLLECT_LIST(NAMED_STRUCT('officer_id', `officer_id`, 'name', `name`)) AS officers FROM __SCHEMA_QUALIFIED__.`border_officers` WHERE `zone` = 'B' GROUP BY `at_post`
