# Expected Structure

## Tables

| Table | Grain | Primary key |
|---|---|---|
| `dim_customer` | One row per synthetic customer | `customer_key` |
| `dim_product` | One row per synthetic product | `product_key` |
| `dim_store` | One row per synthetic store | `store_key` |
| `dim_date` | One row per calendar date | `date_key` |
| `fact_sales` | One row per synthetic sales transaction | `sales_key` |

## Columns

### `dim_customer`

- `customer_key`
- `customer_id`
- `customer_name`
- `email`
- `customer_segment`
- `signup_date`

### `dim_product`

- `product_key`
- `product_id`
- `product_name`
- `category`
- `unit_price`

### `dim_store`

- `store_key`
- `store_id`
- `store_name`
- `region`

### `dim_date`

- `date_key`
- `calendar_date`
- `fiscal_year`
- `month_name`

### `fact_sales`

- `sales_key`
- `customer_key`
- `product_key`
- `store_key`
- `date_key`
- `quantity`
- `gross_amount`
- `discount_amount`
- `net_amount`

## Validation checks

- Every primary key is non-null and unique.
- Every fact foreign key references a valid dimension key.
- Sales amounts reconcile: `net_amount = gross_amount - discount_amount`.
- Retail behavior is deterministic when the same seed and row counts are used.
- No production or user data is read by the example.
