-- Parameters are supplied by Python in metrics_parameters (one row).
-- A paid purchase line has positive quantity AND positive retailer proceeds.
CREATE OR REPLACE TEMP TABLE scoped_transactions AS
SELECT t.* FROM raw_transactions t CROSS JOIN metrics_parameters p
WHERE t.day BETWEEN p.window_start_day AND p.as_of_day;

CREATE OR REPLACE TEMP TABLE eligible_lines AS
SELECT * FROM scoped_transactions WHERE quantity > 0 AND sales_value > 0;

CREATE OR REPLACE TEMP TABLE basket_metrics AS
SELECT household_key, basket_id, day,
       count(*) AS eligible_line_rows,
       sum(sales_value) AS eligible_sales_value
FROM eligible_lines GROUP BY household_key, basket_id, day;

CREATE OR REPLACE TEMP TABLE purchase_intervals AS
SELECT *, day - lag(day) OVER (
    PARTITION BY household_key ORDER BY day, basket_id
) AS days_since_previous_basket
FROM basket_metrics;

CREATE OR REPLACE TEMP TABLE customer_metrics AS
WITH population AS (
    -- Keep previously observed households even if inactive in this window.
    SELECT DISTINCT household_key FROM raw_transactions
    WHERE day <= (SELECT as_of_day FROM metrics_parameters)
), purchases AS (
    SELECT household_key, count(*) AS purchase_baskets,
           count(DISTINCT day) AS purchase_days,
           sum(eligible_sales_value) AS eligible_sales_value,
           min(day) AS first_purchase_day_in_window,
           max(day) AS last_purchase_day_in_window,
           avg(days_since_previous_basket) AS mean_days_between_baskets,
           median(days_since_previous_basket) AS median_days_between_baskets
    FROM purchase_intervals GROUP BY household_key
)
SELECT h.household_key, p.window_start_day, p.as_of_day,
       p.as_of_day - p.window_start_day + 1 AS window_days,
       coalesce(a.purchase_baskets, 0) AS purchase_baskets,
       coalesce(a.purchase_days, 0) AS purchase_days,
       coalesce(a.eligible_sales_value, 0)::DECIMAL(18,2) AS eligible_sales_value,
       a.eligible_sales_value / nullif(a.purchase_baskets, 0) AS average_basket_value,
       a.first_purchase_day_in_window, a.last_purchase_day_in_window,
       p.as_of_day - a.last_purchase_day_in_window AS recency_days,
       coalesce(a.purchase_baskets,0) * 30.0 /
           (p.as_of_day-p.window_start_day+1) AS baskets_per_30_window_days,
       coalesce(a.purchase_baskets,0) >= 2 AS repeat_buyer,
       coalesce(a.purchase_days,0) >= 2 AS multi_day_buyer,
       a.mean_days_between_baskets, a.median_days_between_baskets
FROM population h CROSS JOIN metrics_parameters p
LEFT JOIN purchases a USING(household_key);
