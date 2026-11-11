-- =====================================================================
-- 04_analysis.sql
-- Business questions answered in SQL.
-- Conventions
--   * Revenue = item price of DELIVERED orders (freight reported separately)
--   * Trend analysis uses Jan 2017 – Aug 2018 (edge months are partial, see DQ5)
--   * Customers are counted by customer_unique_id (the real person)
-- Each query starts with "-- @name:" so scripts/export_results.py can save
-- its output to results/<name>.csv for charts and Power BI checks.
-- =====================================================================

SET search_path TO olist;

-- @name: q01_kpi_overview
-- Headline KPIs for the analysis window
WITH delivered AS (
    SELECT o.order_id, c.customer_unique_id, i.price, i.freight_value
    FROM orders o
    JOIN customers c   ON c.customer_id = o.customer_id
    JOIN order_items i ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
)
SELECT
    COUNT(DISTINCT order_id)                                   AS orders,
    COUNT(DISTINCT customer_unique_id)                         AS customers,
    ROUND(SUM(price), 0)                                       AS revenue_brl,
    ROUND(SUM(freight_value), 0)                               AS freight_brl,
    ROUND(SUM(price) / COUNT(DISTINCT order_id), 2)            AS avg_order_value_brl,
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT order_id), 2)     AS items_per_order
FROM delivered;

-- @name: q02_monthly_revenue
-- Monthly revenue with month-over-month growth and running total (window functions)
WITH monthly AS (
    SELECT DATE_TRUNC('month', o.order_purchase_timestamp)::date AS month,
           COUNT(DISTINCT o.order_id)                            AS orders,
           SUM(i.price)                                          AS revenue
    FROM orders o
    JOIN order_items i ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY 1
)
SELECT month,
       orders,
       ROUND(revenue, 0)                                                      AS revenue_brl,
       ROUND(revenue / orders, 2)                                             AS aov_brl,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
                   / LAG(revenue) OVER (ORDER BY month), 1)                   AS mom_growth_pct,
       ROUND(SUM(revenue) OVER (ORDER BY month), 0)                           AS running_revenue_brl
FROM monthly
ORDER BY month;

-- @name: q03_year_over_year
-- Same months, two years: Jan–Aug 2017 vs Jan–Aug 2018
SELECT EXTRACT(YEAR FROM o.order_purchase_timestamp)::int AS year,
       COUNT(DISTINCT o.order_id)                           AS orders,
       ROUND(SUM(i.price), 0)                               AS revenue_brl
FROM orders o
JOIN order_items i ON i.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND EXTRACT(MONTH FROM o.order_purchase_timestamp) BETWEEN 1 AND 8
  AND EXTRACT(YEAR  FROM o.order_purchase_timestamp) IN (2017, 2018)
GROUP BY 1
ORDER BY 1;

-- @name: q04_top_categories
-- Top 15 categories by revenue, with share of total and cumulative share
WITH cat AS (
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
           COUNT(DISTINCT o.order_id) AS orders,
           SUM(i.price)               AS revenue,
           AVG(i.price)               AS avg_item_price
    FROM orders o
    JOIN order_items i ON i.order_id = o.order_id
    JOIN products p    ON p.product_id = i.product_id
    LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY 1
),
ranked AS MATERIALIZED (   -- MATERIALIZED: compute all ranks before filtering
    SELECT category, orders, revenue, avg_item_price,
           RANK() OVER (ORDER BY revenue DESC)                          AS revenue_rank,
           100.0 * revenue / SUM(revenue) OVER ()                       AS share_pct,
           100.0 * SUM(revenue) OVER (ORDER BY revenue DESC
                                      ROWS UNBOUNDED PRECEDING)
                 / SUM(revenue) OVER ()                                 AS cumulative_share_pct
    FROM cat
)
SELECT revenue_rank, category, orders,
       ROUND(revenue, 0)              AS revenue_brl,
       ROUND(avg_item_price, 2)       AS avg_item_price_brl,
       ROUND(share_pct, 1)            AS share_pct,
       ROUND(cumulative_share_pct, 1) AS cumulative_share_pct
FROM ranked
WHERE revenue_rank <= 15
ORDER BY revenue_rank;

-- @name: q05_delivery_vs_reviews
-- Does late delivery hurt review scores?
WITH order_review AS (
    SELECT order_id, AVG(review_score) AS score      -- some orders have >1 review
    FROM order_reviews GROUP BY order_id
),
deliveries AS (
    SELECT o.order_id,
           CASE
             WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date THEN 'On time / early'
             WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date + INTERVAL '7 days' THEN 'Late 1–7 days'
             ELSE 'Late 8+ days'
           END AS delivery_status,
           EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400 AS days_to_deliver
    FROM orders o
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
)
SELECT d.delivery_status,
       COUNT(*)                                                     AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)           AS pct_of_orders,
       ROUND(AVG(d.days_to_deliver)::numeric, 1)                    AS avg_days_to_deliver,
       ROUND(AVG(r.score), 2)                                       AS avg_review_score,
       ROUND(100.0 * AVG(CASE WHEN r.score <= 2 THEN 1 ELSE 0 END), 1) AS pct_1_or_2_star
FROM deliveries d
JOIN order_review r USING (order_id)
GROUP BY d.delivery_status
ORDER BY MIN(d.days_to_deliver);

-- @name: q06_delivery_by_state
-- Delivery speed and lateness by customer state (states with 500+ orders)
SELECT c.customer_state AS state,
       COUNT(*)         AS orders,
       ROUND(AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400)::numeric, 1)
                        AS avg_days_to_deliver,
       ROUND(100.0 * AVG(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END), 1)
                        AS pct_late
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_purchase_timestamp >= '2017-01-01'
  AND o.order_purchase_timestamp <  '2018-09-01'
GROUP BY c.customer_state
HAVING COUNT(*) >= 500
ORDER BY pct_late DESC;

-- @name: q07_repeat_customers
-- How many customers ever come back?
WITH per_customer AS (
    SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS orders
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT COUNT(*)                                                        AS customers,
       SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END)                    AS repeat_customers,
       ROUND(100.0 * AVG(CASE WHEN orders >= 2 THEN 1 ELSE 0 END), 2)  AS repeat_rate_pct,
       MAX(orders)                                                     AS max_orders_by_one_customer
FROM per_customer;

-- @name: q08_cohort_retention
-- Monthly cohort retention: % of each first-purchase cohort that ordered again N months later
WITH cust_orders AS (
    SELECT c.customer_unique_id,
           DATE_TRUNC('month', o.order_purchase_timestamp)::date AS order_month
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
first_month AS (
    SELECT customer_unique_id, MIN(order_month) AS cohort_month
    FROM cust_orders GROUP BY 1
),
activity AS (
    SELECT DISTINCT f.cohort_month,
           (EXTRACT(YEAR FROM AGE(co.order_month, f.cohort_month)) * 12
            + EXTRACT(MONTH FROM AGE(co.order_month, f.cohort_month)))::int AS month_number,
           co.customer_unique_id
    FROM cust_orders co
    JOIN first_month f USING (customer_unique_id)
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS customers FROM first_month GROUP BY 1
)
SELECT a.cohort_month,
       s.customers                                                  AS cohort_customers,
       a.month_number,
       COUNT(DISTINCT a.customer_unique_id)                         AS active_customers,
       ROUND(100.0 * COUNT(DISTINCT a.customer_unique_id) / s.customers, 2) AS retention_pct
FROM activity a
JOIN cohort_size s USING (cohort_month)
WHERE a.month_number BETWEEN 0 AND 6
GROUP BY a.cohort_month, s.customers, a.month_number
ORDER BY a.cohort_month, a.month_number;

-- @name: q09_rfm_segments
-- RFM segmentation (Recency, Frequency, Monetary) scored with NTILE
-- Snapshot date = day after the last order in the window
WITH base AS (
    SELECT c.customer_unique_id,
           MAX(o.order_purchase_timestamp)  AS last_order,
           COUNT(DISTINCT o.order_id)       AS frequency,
           SUM(i.price)                     AS monetary
    FROM orders o
    JOIN customers c   ON c.customer_id = o.customer_id
    JOIN order_items i ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY c.customer_unique_id
),
scored AS (
    SELECT *,
           ('2018-09-01'::date - last_order::date)                 AS recency_days,
           NTILE(5) OVER (ORDER BY last_order)                     AS r_score,   -- 5 = most recent
           CASE WHEN frequency >= 3 THEN 5 WHEN frequency = 2 THEN 4 ELSE 1 END AS f_score,
           -- frequency is 1 for ~97% of customers, so NTILE would split ties
           -- arbitrarily; a rule-based score is more honest here
           NTILE(5) OVER (ORDER BY monetary)                       AS m_score
    FROM base
),
segmented AS (
    SELECT *,
           CASE
             WHEN f_score >= 4 AND r_score >= 4                    THEN 'Loyal - active'
             WHEN f_score >= 4                                     THEN 'Loyal - lapsing'
             WHEN r_score >= 4 AND m_score >= 4                    THEN 'New high-value'
             WHEN r_score >= 4                                     THEN 'New low-value'
             WHEN r_score <= 2 AND m_score >= 4                    THEN 'High-value at risk'
             WHEN r_score <= 2                                     THEN 'Lost low-value'
             ELSE 'Middle'
           END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*)                                               AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)     AS pct_customers,
       ROUND(SUM(monetary), 0)                                AS revenue_brl,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_revenue,
       ROUND(AVG(recency_days), 0)                            AS avg_recency_days,
       ROUND(AVG(monetary), 2)                                AS avg_spend_brl
FROM segmented
GROUP BY segment
ORDER BY revenue_brl DESC;

-- @name: q10_pareto_customers
-- What share of revenue comes from the top 20% of customers?
WITH spend AS (
    SELECT c.customer_unique_id, SUM(i.price) AS revenue
    FROM orders o
    JOIN customers c   ON c.customer_id = o.customer_id
    JOIN order_items i ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY 1
),
ranked AS (
    SELECT revenue, NTILE(10) OVER (ORDER BY revenue DESC) AS decile FROM spend
)
SELECT decile,
       COUNT(*)                                                         AS customers,
       ROUND(SUM(revenue), 0)                                           AS revenue_brl,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1)       AS pct_revenue,
       ROUND(100.0 * SUM(SUM(revenue)) OVER (ORDER BY decile)
                   / SUM(SUM(revenue)) OVER (), 1)                      AS cumulative_pct_revenue
FROM ranked
GROUP BY decile
ORDER BY decile;

-- @name: q11_seller_concentration
-- Seller concentration: share of revenue from the top 10% of sellers
WITH s AS (
    SELECT i.seller_id, SUM(i.price) AS revenue
    FROM orders o JOIN order_items i ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY 1
),
r AS (SELECT revenue, NTILE(10) OVER (ORDER BY revenue DESC) AS decile FROM s)
SELECT COUNT(*)                                                                  AS sellers,
       ROUND(100.0 * SUM(CASE WHEN decile = 1 THEN revenue END) / SUM(revenue), 1) AS top10pct_share_of_revenue
FROM r;

-- @name: q12_payment_mix
-- Payment methods and instalment behaviour
SELECT p.payment_type,
       COUNT(DISTINCT p.order_id)                                       AS orders,
       ROUND(100.0 * COUNT(DISTINCT p.order_id)
             / SUM(COUNT(DISTINCT p.order_id)) OVER (), 1)              AS pct_orders,
       ROUND(SUM(p.payment_value), 0)                                   AS value_brl,
       ROUND(AVG(p.payment_value), 2)                                   AS avg_payment_brl,
       ROUND(AVG(p.payment_installments), 1)                            AS avg_installments
FROM order_payments p
JOIN orders o ON o.order_id = p.order_id
WHERE o.order_status = 'delivered'
  AND p.payment_type <> 'not_defined'
GROUP BY p.payment_type
ORDER BY orders DESC;

-- @name: q13_weekday_hour
-- When do customers buy? (orders by weekday and hour — heatmap input)
SELECT TO_CHAR(order_purchase_timestamp, 'ID')::int  AS weekday_num,   -- 1 = Monday
       TRIM(TO_CHAR(order_purchase_timestamp, 'Day')) AS weekday,
       EXTRACT(HOUR FROM order_purchase_timestamp)::int AS hour,
       COUNT(*) AS orders
FROM orders
WHERE order_purchase_timestamp >= '2017-01-01'
  AND order_purchase_timestamp <  '2018-09-01'
GROUP BY 1, 2, 3
ORDER BY 1, 3;
