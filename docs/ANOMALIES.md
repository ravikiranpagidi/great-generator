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


## Labeled anomaly ground truth

Set `return_labels=True` when you want an answer key for every planted defect.

```python
data = generate_domain(
    "ecommerce",
    anomalies={"null_rate": 0.02, "invalid_status_rate": 0.005},
    return_labels=True,
)

labels = data["_anomaly_labels"]
```

The label table includes the table name, row index, primary key value, affected column, anomaly type, original value, and corrupted value. This is useful for data-quality tool demos, anomaly detection benchmarks, and repeatable QA tests.
