# Supported Schema Inputs

`generate_from_schema` is the primary entry point when you already know the structure of the data you need.

## Current support matrix

| Input | Status | Notes |
|---|---|---|
| Plain Python mapping | Supported | Values are data types, for example `{"age": "int"}` |
| Pandas dtype mapping | Supported | `df.dtypes.to_dict()` can be passed directly |
| Pandas DataFrame | Supported | Empty and populated frames can provide column names and dtypes |
| Compact DDL | Supported | Column list such as `"id int, name string"`; not a full SQL statement |
| Spark `struct<...>` text | Supported | Parsed as compact DDL |
| PySpark `StructType` | Supported | Common scalar fields are preserved; requires an active or explicit SparkSession for Spark output |
| PySpark DataFrame | Supported | Schema and SparkSession are inferred from the input |
| `TableSchema` | Supported | Native typed schema object |
| `DomainSchema` | Supported | Returns a dictionary of generated tables |
| Rich inline metadata mapping | Partially supported | Put metadata in `custom_rules` today; inline field objects are planned |
| Full SQL `CREATE TABLE` | Planned | Dialect-aware DDL parsing is not implemented |
| JSON Schema | Planned | JSON recipe files are a separate feature |
| YAML schema profile | Planned | Simple YAML dataset recipes are supported, not YAML schema inputs |
| Column-name list | Planned | Types are currently required |
| SQLAlchemy model | Planned | ORM inspection is not implemented |
| Pydantic model | Planned | Model inspection is not implemented |
| Dataclass | Planned | Dataclass field inspection is not implemented |

## Plain mapping

```python
from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "customer_name": "string",
    "email": "string",
    "age": "int",
    "balance": "float",
    "created_at": "datetime",
}

df = generate_from_schema(schema, rows=1000)
```

## Pandas schema

```python
import pandas as pd

from great_generator import generate_from_schema

empty = pd.DataFrame(
    {
        "customer_id": pd.Series(dtype="string"),
        "customer_name": pd.Series(dtype="string"),
        "age": pd.Series(dtype="int64"),
        "balance": pd.Series(dtype="float64"),
        "created_at": pd.Series(dtype="datetime64[ns]"),
    }
)

from_frame = generate_from_schema(empty, rows=1000)
from_dtypes = generate_from_schema(empty.dtypes.to_dict(), rows=1000)
```

## Compact DDL

```python
df = generate_from_schema(
    "customer_id string, customer_name string, age int, balance decimal(12,2)",
    rows=1000,
)
```

Supported compact forms include `name type`, `name:type`, and Spark-style `struct<name:type,...>`. Full `CREATE TABLE` statements are not accepted.

## PySpark StructType

```python
from pyspark.sql import types as T

from great_generator import generate_from_schema

schema = T.StructType(
    [
        T.StructField("customer_id", T.StringType(), False),
        T.StructField("customer_name", T.StringType(), True),
        T.StructField("age", T.IntegerType(), True),
        T.StructField("balance", T.DoubleType(), True),
        T.StructField("created_at", T.TimestampType(), True),
    ]
)

spark_df = generate_from_schema(schema, rows=1000, engine="spark")
```

If the runtime cannot discover an active session, pass `spark=spark`. Single-table Spark schema generation currently generates values locally before creating the Spark DataFrame, so choose row counts that fit the driver. Spark-native arbitrary-schema generation is planned.

## Business rules

Inline metadata values are not yet schema inputs. Use a simple schema plus `custom_rules`:

```python
rules = {
    "customer_id": {"prefix": "CUST"},
    "customer_name": {"type": "full_name"},
    "age": {"min": 18, "max": 85},
    "status": {"values": ["Active", "Inactive", "Pending"]},
    "created_at": {"start": "2024-01-01", "end": "2024-12-31"},
}

df = generate_from_schema(schema, rows=1000, custom_rules=rules)
```

Supported rules are `type`, `min`, `max`, `values`, `weighted_values`, `prefix`, `pattern`, `start`, `end`, `null_rate`, and the validation expectation `unique`.

## Output behavior

- Mapping, compact DDL, Pandas, and `TableSchema` inputs return a Pandas DataFrame by default.
- Spark context or `engine="spark"` returns a Spark DataFrame.
- A PySpark DataFrame carries its own schema and Spark session.
- `DomainSchema` returns a dictionary of table-name to DataFrame.

The returned DataFrame remains yours to write to CSV, JSON, Parquet, Delta, a database, or cloud storage.
