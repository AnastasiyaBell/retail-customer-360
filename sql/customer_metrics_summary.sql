SELECT
    (SELECT window_start_day FROM metrics_parameters) AS window_start_day,
    (SELECT as_of_day FROM metrics_parameters) AS as_of_day,
    count(*) AS observed_households,
    count(*) FILTER (WHERE purchase_baskets > 0) AS purchasing_households,
    sum(purchase_baskets) AS purchase_baskets,
    sum(eligible_sales_value) AS eligible_sales_value,
    sum(eligible_sales_value) / nullif(sum(purchase_baskets),0) AS average_basket_value,
    sum(purchase_baskets) * 1.0 / nullif(count(*) FILTER (WHERE purchase_baskets>0),0)
        AS baskets_per_purchasing_household,
    avg(purchase_baskets) AS baskets_per_observed_household,
    count(*) FILTER (WHERE repeat_buyer) AS repeat_buyers,
    100.0 * count(*) FILTER (WHERE repeat_buyer) /
        nullif(count(*) FILTER (WHERE purchase_baskets>0),0) AS repeat_buyer_pct,
    count(*) FILTER (WHERE multi_day_buyer) AS multi_day_buyers,
    100.0 * count(*) FILTER (WHERE multi_day_buyer) /
        nullif(count(*) FILTER (WHERE purchase_baskets>0),0) AS multi_day_buyer_pct,
    (SELECT avg(days_since_previous_basket) FROM purchase_intervals)
        AS mean_days_between_baskets_pooled,
    (SELECT median(days_since_previous_basket) FROM purchase_intervals)
        AS median_days_between_baskets_pooled
FROM customer_metrics
