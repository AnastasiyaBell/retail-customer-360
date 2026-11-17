-- One row per household seen purchasing by the cutoff.
-- Label construction is separate; this query never reads future rows.
SELECT household_key, {cutoff}::INTEGER AS cutoff_day,
    {cutoff}-max(day) AS recency,
    {cutoff}-min(day)+1 AS observed_history_days,
    count(*) FILTER (WHERE day>{cutoff}-30) AS frequency_30,
    count(*) FILTER (WHERE day>{cutoff}-60) AS frequency_60,
    count(*) FILTER (WHERE day>{cutoff}-90) AS frequency_90,
    count(*) FILTER (WHERE day>{cutoff}-{lookback}) AS frequency_180,
    coalesce(sum(eligible_sales_value) FILTER (WHERE day>{cutoff}-30),0) AS monetary_30,
    coalesce(sum(eligible_sales_value) FILTER (WHERE day>{cutoff}-{lookback}),0)
        AS monetary_180,
    count(DISTINCT day) FILTER (WHERE day>{cutoff}-{lookback}) AS purchase_days_180
FROM all_baskets WHERE day<={cutoff}
GROUP BY household_key
