-- =====================================================================
-- 03_data_quality.sql
-- Validate the data before analysing it. Each check returns one row:
-- check name, rows affected, and whether it needs handling downstream.
-- =====================================================================

SET search_path TO olist;

-- ---------------------------------------------------------------
-- DQ1. Row counts per table
-- ---------------------------------------------------------------
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'sellers',        COUNT(*) FROM sellers
UNION ALL SELECT 'products',       COUNT(*) FROM products
UNION ALL SELECT 'orders',         COUNT(*) FROM orders
UNION ALL SELECT 'order_items',    COUNT(*) FROM order_items
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews',  COUNT(*) FROM order_reviews
ORDER BY table_name;

-- ---------------------------------------------------------------
-- DQ2. Issue log — one row per check
-- ---------------------------------------------------------------
WITH checks AS (
    SELECT 'Orders with no items' AS check_name,
           COUNT(*) AS rows_affected,
           'Excluded from revenue (mostly canceled/unavailable)' AS handling
    FROM orders o
    WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = o.order_id)

    UNION ALL
    SELECT 'Orders with no payment record', COUNT(*), 'Kept; revenue uses item prices, not payments'
    FROM orders o
    WHERE NOT EXISTS (SELECT 1 FROM order_payments p WHERE p.order_id = o.order_id)

    UNION ALL
    SELECT 'Delivered orders missing delivery date', COUNT(*), 'Excluded from delivery-time metrics'
    FROM orders
    WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL

    UNION ALL
    SELECT 'Delivered before purchase (impossible dates)', COUNT(*), 'Excluded from delivery-time metrics'
    FROM orders
    WHERE order_delivered_customer_date < order_purchase_timestamp

    UNION ALL
    SELECT 'Products with no category', COUNT(*), 'Labelled "unknown"'
    FROM products
    WHERE product_category_name IS NULL

    UNION ALL
    SELECT 'Categories with no English translation', COUNT(DISTINCT p.product_category_name),
           'Fall back to the Portuguese name'
    FROM products p
    LEFT JOIN category_translation t USING (product_category_name)
    WHERE p.product_category_name IS NOT NULL AND t.product_category_name IS NULL

    UNION ALL
    SELECT 'Duplicate review_id values', COUNT(*) - COUNT(DISTINCT review_id),
           'No PK on reviews; average score per order instead'
    FROM order_reviews

    UNION ALL
    SELECT 'Orders with more than one review', COUNT(*), 'Average score per order'
    FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*) > 1) x

    UNION ALL
    SELECT 'Items with price <= 0', COUNT(*), 'None found = no action'
    FROM order_items WHERE price <= 0

    UNION ALL
    SELECT 'Payments with value 0', COUNT(*), 'Vouchers/adjustments; kept'
    FROM order_payments WHERE payment_value = 0

    UNION ALL
    SELECT 'Customers (order-level IDs) vs unique people',
           COUNT(*) - COUNT(DISTINCT customer_unique_id),
           'Use customer_unique_id for repeat/retention analysis'
    FROM customers
)
SELECT * FROM checks ORDER BY rows_affected DESC;

-- ---------------------------------------------------------------
-- DQ3. Payments vs item totals — do they reconcile?
-- (A difference usually means interest on instalments or vouchers.)
-- ---------------------------------------------------------------
WITH item_tot AS (
    SELECT order_id, SUM(price + freight_value) AS items_total
    FROM order_items GROUP BY order_id
),
pay_tot AS (
    SELECT order_id, SUM(payment_value) AS paid_total
    FROM order_payments GROUP BY order_id
)
SELECT
    COUNT(*)                                                        AS orders_compared,
    SUM(CASE WHEN ABS(paid_total - items_total) <= 1 THEN 1 ELSE 0 END) AS match_within_1_brl,
    ROUND(100.0 * SUM(CASE WHEN ABS(paid_total - items_total) <= 1 THEN 1 ELSE 0 END) / COUNT(*), 1)
                                                                    AS pct_matching
FROM item_tot JOIN pay_tot USING (order_id);

-- ---------------------------------------------------------------
-- DQ4. Price outliers (IQR rule) — reported, not removed:
-- expensive items are real sales, not errors.
-- ---------------------------------------------------------------
WITH q AS (
    SELECT percentile_cont(0.25) WITHIN GROUP (ORDER BY price) AS q1,
           percentile_cont(0.75) WITHIN GROUP (ORDER BY price) AS q3
    FROM order_items
)
SELECT ROUND(q1::numeric,2) AS q1, ROUND(q3::numeric,2) AS q3,
       ROUND((q3 + 1.5*(q3-q1))::numeric,2) AS upper_fence,
       (SELECT COUNT(*) FROM order_items, q WHERE price > q3 + 1.5*(q3-q1)) AS items_above_fence,
       (SELECT MAX(price) FROM order_items) AS max_price
FROM q;

-- ---------------------------------------------------------------
-- DQ5. Date coverage — months at the edges are partial
-- ---------------------------------------------------------------
SELECT DATE_TRUNC('month', order_purchase_timestamp)::date AS month,
       COUNT(*) AS orders
FROM orders
GROUP BY 1
ORDER BY 1;
