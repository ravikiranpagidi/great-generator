# Realistic Values

Great Generator has two modes:

- `realism="placeholder"`: simple deterministic values such as `customer_name_1`
- `realism="realistic"`: believable business values such as `Emily Carter`, `emily.carter247@example.com`, `Amazon`, `Checking`, and `Wireless Mouse`

The realistic layer recognizes common field names:

- person fields: `customer_name`, `patient_name`, `employee_name`, `user_name`, `resident_name`, `first_name`, `last_name`
- contact fields: `email`, `phone_number`, `street_address`, `city`, `state`, `postal_code`
- business fields: `company_name`, `organization_name`, `merchant_name`, `product_name`, `provider_name`, `facility_name`, `carrier_name`
- domain values: account types, transaction types, order statuses, claim statuses, policy types, plan names, feature names, and more

The layer preserves relationships. Primary keys and foreign keys are not rewritten.

Pandas mode uses Faker-backed deterministic generation. Spark mode uses deterministic Spark-native expressions and curated values so it remains cluster-friendly.


## Semantic schema generation

`generate_from_schema(...)` uses semantic-field inference for realistic schema-driven data. It does not only call Faker for a few obvious fields. It first normalizes the column name, expands common abbreviations, checks the declared data type, and then chooses a generation strategy.

Examples:

| Column | Type | Inferred behavior |
| --- | --- | --- |
| `customer_name` | `string` | full names |
| `cust_name` | `string` | full names |
| `emp_name` | `string` | full names |
| `firstName` | `string` | first names |
| `email_id` | `string` | email addresses |
| `mobile_no` | `string` | phone numbers |
| `zip_code` | `string` | postal codes |
| `employee_age` | `int` | working-age adults |
| `salary` | `double` | salary range |
| `created_at` | `timestamp` | recent timestamps |
| `order_status` | `string` | order status values |

```python
from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "cust_name": "string",
    "email_id": "string",
    "mobile_no": "string",
    "employee_age": "int",
    "salary": "double",
}

df = generate_from_schema(schema, rows=100, domain="hr")
```

Use `realistic=False` if you need the older placeholder-style behavior.

## Custom rules

```python
df = generate_from_schema(
    schema,
    rows=100,
    custom_rules={
        "employee_age": {"min": 25, "max": 55},
        "salary": {"min": 60000, "max": 160000},
        "customer_id": {"prefix": "CUST", "unique": True},
        "status": {"values": ["Active", "Inactive"]},
    },
)
```

## Cross-field consistency

Where practical, schema generation keeps related fields aligned:

- `first_name`, `last_name`, `full_name`, and `email` are generated from the same person record.
- `updated_at` is generated after `created_at`.
- `end_date` is generated after `start_date`.
- `total_amount` is generated from `quantity * unit_price` when those fields exist.
- `age` is aligned with `date_of_birth` when both fields exist.

## Validation

```python
from great_generator import validate_generated_data

result = validate_generated_data(df, schema)
```

The validator returns `passed`, `errors`, and `warnings` and checks common issues such as invalid emails, unrealistic ages, duplicate IDs, numeric range violations, date relationship violations, and amount calculation mismatches.

## Known limitations

Semantic inference is intentionally practical, not magical. Ambiguous column names can still need `custom_rules`. Faker improves variety when installed, and Great Generator also includes lightweight fallbacks so schema generation remains usable in constrained environments.
