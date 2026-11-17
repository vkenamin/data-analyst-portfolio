-- =====================================================================
-- 05_powerbi_views.sql
-- Star schema for Power BI (connect with Get Data > PostgreSQL database
-- and pick the bi.* views). Cleaning rules from 03_data_quality.sql are
-- applied here once, so every report uses the same definitions.
--
--   fact_sales  (one row per order item)  ─┬─ dim_date
--   fact_orders (one row per order)       ─┼─ dim_customer
--                                          ├─ dim_product
--                                          └─ dim_seller
-- =====================================================================

DROP SCHEMA IF EXISTS bi CASCADE;
CREATE SCHEMA bi;

-- ---------------- Dimensions ----------------
CREATE VIEW bi.dim_date AS
SELECT d::date                                   AS date_key,
       EXTRACT(YEAR    FROM d)::int              AS year,
       EXTRACT(QUARTER FROM d)::int              AS quarter,
       EXTRACT(MONTH   FROM d)::int              AS month_num,
       TO_CHAR(d, 'Mon')                         AS month_name,
       DATE_TRUNC('month', d)::date              AS month_start,
       EXTRACT(ISODOW  FROM d)::int              AS weekday_num,
       TRIM(TO_CHAR(d, 'Day'))                   AS weekday_name,
       (EXTRACT(ISODOW FROM d) IN (6, 7))        AS is_weekend
FROM generate_series('2016-09-01'::date, '2018-12-31'::date, INTERVAL '1 day') AS d;

CREATE VIEW bi.dim_customer AS
SELECT customer_id,
       customer_unique_id,
       customer_city,
       customer_state
FROM olist.customers;

CREATE VIEW bi.dim_product AS
SELECT p.product_id,
       COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
       p.product_weight_g,
       p.product_photos_qty
FROM olist.products p
LEFT JOIN olist.category_translation t USING (product_category_name);

CREATE VIEW bi.dim_seller AS
SELECT seller_id, seller_city, seller_state
FROM olist.sellers;

-- ---------------- Facts ----------------
CREATE VIEW bi.fact_sales AS
SELECT i.order_id,
       i.order_item_id,
       o.order_purchase_timestamp::date AS date_key,
       o.customer_id,
       i.product_id,
       i.seller_id,
       o.order_status,
       i.price,
       i.freight_value
FROM olist.order_items i
JOIN olist.orders o ON o.order_id = i.order_id;

CREATE VIEW bi.fact_orders AS
WITH review AS (
    SELECT order_id, AVG(review_score)::numeric(3,2) AS review_score
    FROM olist.order_reviews GROUP BY order_id
),
pay AS (
    SELECT order_id,
           SUM(payment_value)                                   AS payment_value,
           MAX(payment_installments)                            AS installments,
           (ARRAY_AGG(payment_type ORDER BY payment_value DESC))[1] AS main_payment_type
    FROM olist.order_payments GROUP BY order_id
)
SELECT o.order_id,
       o.customer_id,
       o.order_purchase_timestamp::date                         AS date_key,
       o.order_status,
       CASE WHEN o.order_delivered_customer_date >= o.order_purchase_timestamp
            THEN ROUND((EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400)::numeric, 1)
       END                                                      AS days_to_deliver,
       CASE
         WHEN o.order_delivered_customer_date IS NULL                                    THEN NULL
         WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date         THEN 'On time / early'
         WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date + INTERVAL '7 days' THEN 'Late 1–7 days'
         ELSE 'Late 8+ days'
       END                                                      AS delivery_status,
       (o.order_delivered_customer_date > o.order_estimated_delivery_date) AS is_late,
       r.review_score,
       p.payment_value,
       p.installments,
       p.main_payment_type
FROM olist.orders o
LEFT JOIN review r USING (order_id)
LEFT JOIN pay    p USING (order_id);

-- ---------------- Customer segments (RFM) ----------------
-- Same logic as q09_rfm_segments in 04_analysis.sql, one row per customer,
-- so Power BI can slice segments by state, category, etc.
CREATE VIEW bi.customer_rfm AS
WITH base AS (
    SELECT c.customer_unique_id,
           MAX(o.order_purchase_timestamp) AS last_order,
           COUNT(DISTINCT o.order_id)      AS frequency,
           SUM(i.price)                    AS monetary
    FROM olist.orders o
    JOIN olist.customers c   ON c.customer_id = o.customer_id
    JOIN olist.order_items i ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY c.customer_unique_id
),
scored AS (
    SELECT *,
           ('2018-09-01'::date - last_order::date) AS recency_days,
           NTILE(5) OVER (ORDER BY last_order)     AS r_score,
           CASE WHEN frequency >= 3 THEN 5 WHEN frequency = 2 THEN 4 ELSE 1 END AS f_score,
           NTILE(5) OVER (ORDER BY monetary)       AS m_score
    FROM base
)
SELECT customer_unique_id, recency_days, frequency, ROUND(monetary, 2) AS monetary,
       r_score, f_score, m_score,
       CASE
         WHEN f_score >= 4 AND r_score >= 4 THEN 'Loyal - active'
         WHEN f_score >= 4                  THEN 'Loyal - lapsing'
         WHEN r_score >= 4 AND m_score >= 4 THEN 'New high-value'
         WHEN r_score >= 4                  THEN 'New low-value'
         WHEN r_score <= 2 AND m_score >= 4 THEN 'High-value at risk'
         WHEN r_score <= 2                  THEN 'Lost low-value'
         ELSE 'Middle'
       END AS segment
FROM scored;
