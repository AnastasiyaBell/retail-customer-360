-- Same paid-line eligibility and inclusive window as notebook 02.
CREATE TEMP TABLE eda_lines AS
SELECT t.household_key,t.basket_id,t.day,t.product_id,t.store_id,t.week_no,
    t.quantity,t.sales_value,
    t.retail_disc_raw::DECIMAL(18,2) AS retail_disc,
    t.coupon_disc_raw::DECIMAL(18,2) AS coupon_disc,
    t.coupon_match_disc_raw::DECIMAL(18,2) AS coupon_match_disc,
    coalesce(p.department,'[Unmatched product]') AS department,
    coalesce(p.category,'[Unmatched product]') AS category
FROM transaction_context t CROSS JOIN metrics_parameters m
LEFT JOIN product_metadata p USING(product_id)
WHERE t.day BETWEEN m.window_start_day AND m.as_of_day
    AND t.quantity>0 AND t.sales_value>0;

CREATE TEMP TABLE discount_baskets AS
SELECT household_key,basket_id,day,min(week_no) AS week_no,
    bool_or(retail_disc<0) AS has_loyalty_reduction,
    bool_or(coupon_disc<0) AS has_manufacturer_coupon,
    bool_or(coupon_match_disc<0) AS has_coupon_match,
    bool_or(retail_disc>0 OR coupon_disc>0 OR coupon_match_disc>0)
        AS has_positive_adjustment,
    sum(sales_value) AS eligible_sales_value,
    sum(CASE WHEN retail_disc<0 THEN -retail_disc ELSE 0 END) AS loyalty_reduction,
    sum(CASE WHEN coupon_disc<0 THEN -coupon_disc ELSE 0 END) AS manufacturer_reduction,
    sum(CASE WHEN coupon_match_disc<0 THEN -coupon_match_disc ELSE 0 END)
        AS match_reduction
FROM eda_lines GROUP BY household_key,basket_id,day;
