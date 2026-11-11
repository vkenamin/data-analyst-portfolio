-- =====================================================================
-- 02_load_data.sql
-- Load the Kaggle CSVs. Run with psql from the project folder:
--   psql -d portfolio -f sql/02_load_data.sql
-- Expects the CSVs in data/raw/ (see README for the download link).
-- Parents are loaded before children so the foreign keys hold.
-- =====================================================================

SET search_path TO olist;
SET client_encoding TO 'UTF8';   -- review text is Portuguese; Windows psql otherwise defaults to WIN1252

\copy customers            FROM 'data/raw/olist_customers_dataset.csv'            WITH (FORMAT csv, HEADER true)
\copy sellers              FROM 'data/raw/olist_sellers_dataset.csv'              WITH (FORMAT csv, HEADER true)
\copy category_translation FROM 'data/raw/product_category_name_translation.csv'  WITH (FORMAT csv, HEADER true)
\copy products             FROM 'data/raw/olist_products_dataset.csv'             WITH (FORMAT csv, HEADER true)
\copy orders               FROM 'data/raw/olist_orders_dataset.csv'               WITH (FORMAT csv, HEADER true)
\copy order_items          FROM 'data/raw/olist_order_items_dataset.csv'          WITH (FORMAT csv, HEADER true)
\copy order_payments       FROM 'data/raw/olist_order_payments_dataset.csv'       WITH (FORMAT csv, HEADER true)
\copy order_reviews        FROM 'data/raw/olist_order_reviews_dataset.csv'        WITH (FORMAT csv, HEADER true)

ANALYZE;
