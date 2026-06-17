# CDC Simulation

CDC records are useful for testing ingestion pipelines, merge logic, late-arriving data handling, and deduplication.

```python
from great_generator import generate_cdc

cdc = generate_cdc(
    "banking",
    table="customers",
    rows=10000,
    operations=["insert", "update", "delete"],
    late_arrival_rate=0.02,
    duplicate_rate=0.005,
    seed=42,
)
```

CDC output includes:

- operation type
- before payload
- after payload
- event timestamp
- ingestion timestamp
- sequence number
- source system
- late-arriving indicator
- duplicate indicator
