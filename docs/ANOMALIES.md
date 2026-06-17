# Anomaly Injection

By default, generated data is clean and relationship-safe. Use anomaly injection when you intentionally need messy data.

```python
data = generate_domain(
    "ecommerce",
    anomalies={
        "null_rate": 0.02,
        "duplicate_rate": 0.01,
        "orphan_fk_rate": 0.001,
        "late_arrival_rate": 0.02,
        "outlier_rate": 0.005,
    },
    seed=42,
)
```

Supported anomaly categories include:

- nulls
- duplicates
- orphan foreign keys
- late-arriving records
- out-of-order events
- outliers
- skew
- negative amounts
- invalid status codes

Anomalies are opt-in so regular domain generation remains valid by default.
