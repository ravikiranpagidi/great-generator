# Contracts and SQL DDL ingestion

Great Generator now has a canonical contract layer for schema-first data generation. A contract is a typed, Pandas-free and Spark-free description of one or more tables, their columns, keys, constraints, relationships, source dialect, metadata, and stable fingerprint.

Use this guide when your source of truth is SQL DDL from a database, lakehouse, warehouse, Spark notebook, or Databricks workspace.

## Quick example

```python
from great_generator import generate_from_schema, parse_ddl

ddl = """
CREATE TABLE sales.customers (
  customer_id BIGINT PRIMARY KEY,
  customer_name STRING NOT NULL,
  email VARCHAR(120) UNIQUE,
  signup_date DATE
);

CREATE TABLE sales.orders (
  order_id BIGINT PRIMARY KEY,
  customer_id BIGINT NOT NULL,
  amount DECIMAL(12, 2),
  order_date DATE,
  CONSTRAINT fk_orders_customers
    FOREIGN KEY (customer_id) REFERENCES sales.customers(customer_id)
)
"""

contract = parse_ddl(ddl, dialect="databricks")
print(contract.fingerprint())
print(contract.tables["sales.orders"].foreign_keys[0].parent_table)
```

For one-table DDL, generate directly from the contract:

```python
customer_contract = parse_ddl(
    """
    CREATE TABLE customers (
      customer_id BIGINT PRIMARY KEY,
      customer_name STRING,
      email STRING,
      signup_date DATE
    )
    """,
    dialect="databricks",
)

df = generate_from_schema(customer_contract, rows=1000)
```

For multiple related tables, pass row counts by table name:

```python
data = generate_from_schema(
    contract,
    rows={"sales.customers": 1000, "sales.orders": 5000},
)
```

## Public API

```python
parse_ddl(
    ddl_text,
    dialect="ansi",
    strict=True,
    name="ddl_contract",
)
```

Returns a `ContractSchema` from `great_generator.schemas.models`.

Supported dialect values are:

- `"ansi"`
- `"spark"`
- `"databricks"`

The library supports a documented subset of those dialects. It does not claim complete database-specific coverage.

## Contract model

A `ContractSchema` contains:

- contract name, namespace, source format, source dialect, tags, and extension metadata
- one or more `TableSchema` objects
- ordered `ColumnSpec` objects
- single-column and composite primary key metadata
- single-column and composite foreign key metadata
- multiple foreign keys from one table
- self-referencing foreign key metadata
- unique constraints
- check constraints as metadata
- schema-qualified table names
- stable canonical JSON and SHA-256 fingerprint

The model extends the existing schema dataclasses rather than replacing them. Existing `ColumnSpec`, `TableSchema`, `DomainSchema`, and `ForeignKey(column, parent_table, parent_column)` usage remains compatible.

## Canonical serialization and hashing

```python
from great_generator.contracts import canonical_contract_json, contract_hash

canonical_json = canonical_contract_json(contract)
fingerprint = contract_hash(contract)
```

The fingerprint uses SHA-256 over canonical JSON and is suitable for manifests, deterministic seeding, caching, and reproducibility checks.

Normalized in canonical form:

- insignificant SQL whitespace
- dictionary insertion order
- unquoted identifier case
- type-name case and spacing
- constraint ordering where order is not semantically meaningful

Preserved in the contract:

- ordered columns
- quoted identifier case and spaces
- schema-qualified names
- normalized physical type
- source type text for inspection
- key and relationship column order
- default expressions and comments where parsed

Parser diagnostics are excluded from the hash because they describe ingestion observations, not contract semantics.

## Supported DDL subset

| Construct | Status |
|---|---|
| One or more `CREATE TABLE` statements | Supported |
| Schema-qualified table names | Supported |
| Quoted identifiers | Supported |
| Common scalar ANSI types | Supported |
| Spark and Databricks scalar types | Supported |
| `NULL` and `NOT NULL` | Supported |
| Inline primary keys | Supported |
| Table-level primary keys | Supported |
| Composite primary keys | Parsed as metadata |
| Inline foreign keys | Supported |
| Table-level foreign keys | Supported |
| Composite foreign keys | Parsed as metadata |
| Multiple foreign keys | Supported |
| Self-referencing foreign keys | Parsed as metadata |
| Unique constraints | Supported |
| Check constraints | Stored as metadata |
| Defaults | Stored as metadata |
| Column and table comments | Stored as metadata |
| `USING DELTA` and `PARTITIONED BY` | Stored as metadata |

Supported scalar type families include `INT`, `BIGINT`, `STRING`, `VARCHAR`, `CHAR`, `TEXT`, `DECIMAL`, `NUMERIC`, `DOUBLE`, `FLOAT`, `BOOLEAN`, `DATE`, `TIMESTAMP`, `TIMESTAMP_NTZ`, and `BINARY`.

## Strict and permissive parsing

Strict mode is the default:

```python
contract = parse_ddl(ddl, strict=True)
```

Unsupported contract-affecting syntax raises `ContractParseError` with structured diagnostics.

```python
from great_generator.contracts import ContractParseError

try:
    parse_ddl("CREATE TABLE t (id BIGINT GENERATED ALWAYS AS IDENTITY)")
except ContractParseError as exc:
    for diagnostic in exc.diagnostics:
        print(diagnostic.construct, diagnostic.message)
```

Permissive mode can return warnings when the remaining base contract is still safe:

```python
from great_generator.contracts import SQLDDLParser

result = SQLDDLParser().parse(ddl, strict=False)
print(result.warnings)
contract = result.contract
```

Unknown types, malformed column definitions, missing key columns, and unsafe relationship parsing remain errors.

## Generation support versus parsing support

M1A is intentionally a vertical slice:

- full documented DDL parsing to canonical contracts is supported
- one-table parsed DDL contracts generate Pandas or Spark DataFrames through the existing `generate_from_schema` path
- simple multi-table single-column relationships can generate through the existing relational path
- composite-key and cyclic relational generation are parsed as metadata today and planned for a later relational milestone

This distinction keeps claims accurate and prevents users from assuming that every parsed constraint already drives row-generation strategy.

## Migration notes

No migration is required for existing users. Compact DDL strings such as `"id int, name string"`, mappings, Pandas schemas, PySpark schemas, `TableSchema`, and `DomainSchema` continue to work.

New users with full SQL DDL should call `parse_ddl(...)` first, then pass the returned contract to `generate_from_schema(...)`.
