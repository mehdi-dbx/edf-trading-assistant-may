-- Border officer staffing: counts how many officers are at post (ACTIVE), away, or on break. Params: {zone}
SELECT `at_post`, COUNT(*) AS officer_count, COLLECT_LIST(`name`) AS officer_names FROM __SCHEMA_QUALIFIED__.`border_officers` WHERE TRIM(UPPER(`zone`)) = 'ZONE ' || UPPER('{zone}') AND `at_post` IN ('ACTIVE', 'AWAY', 'BREAK') GROUP BY `at_post`
