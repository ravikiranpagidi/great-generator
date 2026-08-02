CREATE TABLE dim_customer (
  customer_key BIGINT PRIMARY KEY,
  customer_id STRING NOT NULL,
  customer_name STRING,
  email STRING,
  customer_segment STRING,
  signup_date DATE
);
CREATE TABLE dim_product (
  product_key BIGINT PRIMARY KEY,
  product_id STRING NOT NULL,
  product_name STRING,
  category STRING,
  unit_price DECIMAL(10,2)
);
CREATE TABLE dim_store (
  store_key BIGINT PRIMARY KEY,
  store_id STRING NOT NULL,
  store_name STRING,
  region STRING
);
CREATE TABLE dim_date (
  date_key BIGINT PRIMARY KEY,
  calendar_date DATE,
  fiscal_year INT,
  month_name STRING
);
CREATE TABLE fact_sales (
  sales_key BIGINT PRIMARY KEY,
  customer_key BIGINT NOT NULL REFERENCES dim_customer(customer_key),
  product_key BIGINT NOT NULL REFERENCES dim_product(product_key),
  store_key BIGINT NOT NULL REFERENCES dim_store(store_key),
  date_key BIGINT NOT NULL REFERENCES dim_date(date_key),
  quantity INT,
  gross_amount DECIMAL(12,2),
  discount_amount DECIMAL(12,2),
  net_amount DECIMAL(12,2)
);
