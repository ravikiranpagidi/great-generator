import pandas as pd
import pytest

from great_generator import generate_relational
from great_generator.schemas.relational import relational_schema_from_specs
from great_generator.utils.validation import validate_foreign_keys


def test_generate_relational_returns_named_pandas_dataframes():
    data = generate_relational(
        tables={
            "customers": {
                "schema": "customer_id int primary key, name string, segment string",
                "rows": 25,
            },
            "orders": {
                "schema": "order_id int primary key, customer_id int, amount double",
                "rows": 100,
            },
            "payments": {
                "schema": "payment_id int primary key, order_id int, status string, amount double",
                "rows": 100,
            },
        },
        relationships=[
            "orders.customer_id -> customers.customer_id",
            "payments.order_id -> orders.order_id",
        ],
    )

    assert set(data) == {"customers", "orders", "payments"}
    assert all(isinstance(frame, pd.DataFrame) for frame in data.values())
    assert len(data["customers"]) == 25
    assert len(data["orders"]) == 100
    assert len(data["payments"]) == 100
    assert data["orders"]["customer_id"].isin(data["customers"]["customer_id"]).all()
    assert data["payments"]["order_id"].isin(data["orders"]["order_id"]).all()


def test_generate_relational_supports_inline_references_and_rows_mapping():
    data = generate_relational(
        tables={
            "customers": "customer_id int primary key, name string",
            "orders": (
                "order_id int primary key, "
                "customer_id int references customers.customer_id, "
                "amount double"
            ),
        },
        rows={"customers": 10, "orders": 40},
    )
    schema, _row_counts = relational_schema_from_specs(
        tables={
            "customers": "customer_id int primary key, name string",
            "orders": (
                "order_id int primary key, "
                "customer_id int references customers.customer_id, "
                "amount double"
            ),
        },
        rows={"customers": 10, "orders": 40},
    )

    assert len(data["customers"]) == 10
    assert len(data["orders"]) == 40
    assert validate_foreign_keys(data, schema)["orders.customer_id"] == 0


def test_generate_relational_returns_dataframes_users_can_write_natively(tmp_path):
    data = generate_relational(
        tables={
            "customers": {
                "schema": "customer_id int primary key, name string",
                "rows": 5,
            },
            "orders": {
                "schema": "order_id int primary key, customer_id int references customers.customer_id",
                "rows": 15,
            },
        }
    )

    customers_csv = tmp_path / "customers.csv"
    orders_parquet = tmp_path / "orders.parquet"

    data["customers"].to_csv(customers_csv, index=False)
    data["orders"].to_parquet(orders_parquet, index=False)

    assert customers_csv.exists()
    assert orders_parquet.exists()


def test_generate_relational_rejects_unknown_relationship_table():
    with pytest.raises(ValueError, match="unknown child table"):
        generate_relational(
            tables={
                "customers": "customer_id int primary key, name string",
            },
            relationships=["orders.customer_id -> customers.customer_id"],
        )


def test_generate_relational_rejects_unknown_relationship_column():
    with pytest.raises(ValueError, match="does not exist"):
        generate_relational(
            tables={
                "customers": "customer_id int primary key, name string",
                "orders": "order_id int primary key, customer_id int",
            },
            relationships=["orders.missing_customer_id -> customers.customer_id"],
        )
