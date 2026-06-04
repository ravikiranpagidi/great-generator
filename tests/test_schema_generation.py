import pandas as pd
import pytest

from great_generator import generate_from_schema, get_domain_schema


def test_generate_from_schema_accepts_ddl_string():
    frame = generate_from_schema(
        "id int, name string, amount decimal(10,2), active boolean, created_at timestamp",
        rows=5,
        seed=42,
    )

    assert list(frame.columns) == ["id", "name", "amount", "active", "created_at"]
    assert len(frame) == 5
    assert frame["id"].tolist() == [1, 2, 3, 4, 5]
    assert frame["name"].iloc[0] == "name_1"
    assert pd.api.types.is_datetime64_any_dtype(frame["created_at"])


def test_generate_from_schema_accepts_empty_pandas_dataframe_with_dtypes():
    schema = pd.DataFrame(
        {
            "customer_id": pd.Series(dtype="int64"),
            "customer_name": pd.Series(dtype="string"),
            "score": pd.Series(dtype="float64"),
            "is_active": pd.Series(dtype="bool"),
            "created_at": pd.Series(dtype="datetime64[ns]"),
        }
    )

    frame = generate_from_schema(schema, rows=3, seed=7)

    assert list(frame.columns) == list(schema.columns)
    assert len(frame) == 3
    assert str(frame["customer_id"].dtype) == "int64"
    assert str(frame["customer_name"].dtype) == "string"
    assert str(frame["score"].dtype) == "float64"
    assert str(frame["is_active"].dtype) == "bool"
    assert pd.api.types.is_datetime64_any_dtype(frame["created_at"])


def test_generate_from_schema_accepts_struct_style_ddl_string():
    frame = generate_from_schema("struct<id:int,name:string,event_date:date>", rows=2, seed=42)

    assert list(frame.columns) == ["id", "name", "event_date"]
    assert frame["id"].tolist() == [1, 2]
    assert str(frame["event_date"].dtype) == "object"


def test_generate_from_schema_keeps_domain_schema_compatibility():
    data = generate_from_schema(get_domain_schema("ecommerce"), rows=2, seed=42)

    assert set(data) == {
        "customers",
        "products",
        "orders",
        "order_items",
        "payments",
        "shipments",
        "returns",
    }
    assert len(data["customers"]) == 2
    assert data["orders"]["customer_id"].isin(data["customers"]["customer_id"]).all()


def test_generate_from_schema_rejects_mapping_rows_for_single_table_schema():
    with pytest.raises(ValueError, match="rows to be an integer"):
        generate_from_schema("id int, name string", rows={"sample": 10})


def test_generate_from_schema_accepts_pyspark_structtype_as_pandas_when_available():
    types = pytest.importorskip("pyspark.sql.types")
    schema = types.StructType(
        [
            types.StructField("id", types.IntegerType(), False),
            types.StructField("name", types.StringType(), True),
            types.StructField("created_at", types.TimestampType(), True),
        ]
    )

    frame = generate_from_schema(schema, rows=4, engine="pandas", seed=42)

    assert list(frame.columns) == ["id", "name", "created_at"]
    assert frame["id"].tolist() == [1, 2, 3, 4]
    assert pd.api.types.is_datetime64_any_dtype(frame["created_at"])
