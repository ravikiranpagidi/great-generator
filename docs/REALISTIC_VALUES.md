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
