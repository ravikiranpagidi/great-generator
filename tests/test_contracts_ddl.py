from __future__ import annotations

import pandas as pd
import pytest

from great_generator import (
    explain_generation_plan,
    generate_from_schema,
    infer_generation_plan,
    parse_ddl,
    validate_generated_data,
)
from great_generator.contracts import (
    ContractParseError,
    SQLDDLParser,
    canonical_contract_json,
    contract_hash,
)
from great_generator.schemas.generation import table_schema_from_ddl
from great_generator.schemas.models import (
    CheckConstraint,
    ColumnSpec,
    ContractSchema,
    ForeignKey,
    TableSchema,
    UniqueConstraint,
)


def test_schema_models_preserve_backward_compatible_constructors():
    column = ColumnSpec("customer_id", "bigint")
    fk = ForeignKey("customer_id", "customers", "customer_id")
    table = TableSchema(
        "orders",
        (column,),
        primary_key="customer_id",
        foreign_keys=(fk,),
    )

    assert table.primary_key == "customer_id"
    assert table.primary_key_columns == ("customer_id",)
    assert fk.column == "customer_id"
    assert fk.child_columns == ("customer_id",)
    assert fk.parent_columns == ("customer_id",)
    assert hash(column)


def test_contract_model_supports_metadata_constraints_and_hashing():
    table = TableSchema(
        name="accounts",
        namespace="banking",
        columns=(
            ColumnSpec("account_id", "bigint", nullable=False, metadata={"source": "ddl"}),
            ColumnSpec("customer_id", "bigint", nullable=False),
            ColumnSpec("status", "string", accepted_values=("active", "closed")),
        ),
        primary_key_columns=("account_id",),
        unique_constraints=(
            UniqueConstraint(("customer_id", "status"), name="uq_customer_status"),
        ),
        checks=(CheckConstraint("account_id > 0", name="ck_account_id", columns=("account_id",)),),
        metadata={"owner": "data_engineering"},
    )
    contract = ContractSchema(
        name="banking_contract",
        namespace="banking",
        tables={table.qualified_name: table},
        source_format="sql_ddl",
        source_dialect="ansi",
        metadata={"env": "test"},
    )

    payload = contract.as_dict()

    assert payload["tables"]["banking.accounts"]["columns"][0]["name"] == "account_id"
    assert contract_hash(contract).startswith("sha256:")
    assert canonical_contract_json(contract) == contract.canonical_json()
    assert contract.fingerprint() == contract_hash(contract)


def test_canonical_hash_ignores_sql_formatting_and_unquoted_case():
    left = parse_ddl(
        "CREATE TABLE Sales.Customers (Customer_ID BIGINT PRIMARY KEY, Name STRING)",
        dialect="databricks",
    )
    right = parse_ddl(
        """
        create table sales.customers (
          customer_id bigint primary key,
          name string
        )
        """,
        dialect="databricks",
    )

    assert left.fingerprint() == right.fingerprint()


def test_parse_one_table_with_columns_constraints_and_defaults():
    ddl = """
    CREATE TABLE sales.customers (
      customer_id BIGINT PRIMARY KEY,
      customer_name STRING NOT NULL COMMENT 'display name',
      email VARCHAR(120) UNIQUE,
      credit_limit DECIMAL(12, 2) DEFAULT 1000.00,
      active BOOLEAN DEFAULT true,
      created_at TIMESTAMP DEFAULT current_timestamp(),
      CONSTRAINT ck_credit CHECK (credit_limit >= 0)
    ) COMMENT 'customer master'
    """

    contract = parse_ddl(ddl, dialect="databricks")
    table = contract.tables["sales.customers"]

    assert isinstance(contract, ContractSchema)
    assert table.name == "customers"
    assert table.namespace == "sales"
    assert table.primary_key_columns == ("customer_id",)
    assert table.description == "customer master"
    assert table.column_names() == [
        "customer_id",
        "customer_name",
        "email",
        "credit_limit",
        "active",
        "created_at",
    ]
    assert table.columns[0].dtype == "bigint"
    assert table.columns[0].nullable is False
    assert table.columns[1].description == "display name"
    assert table.columns[2].max_length == 120
    assert table.columns[3].dtype == "decimal"
    assert table.columns[3].precision == 12
    assert table.columns[3].scale == 2
    assert table.columns[3].default_expression == "1000.00"
    assert table.unique_constraints[0].columns == ("email",)
    assert table.checks[0].name == "ck_credit"


def test_parse_multiple_tables_with_composite_keys_and_relationships():
    ddl = """
    CREATE TABLE sales.customers (
      customer_id BIGINT PRIMARY KEY,
      parent_customer_id BIGINT REFERENCES sales.customers(customer_id),
      customer_name STRING
    );
    CREATE TABLE sales.orders (
      order_id BIGINT,
      line_id INT,
      customer_id BIGINT NOT NULL,
      billing_customer_id BIGINT,
      CONSTRAINT pk_orders PRIMARY KEY (order_id, line_id),
      CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id)
        REFERENCES sales.customers(customer_id) ON DELETE CASCADE,
      CONSTRAINT fk_orders_billing FOREIGN KEY (billing_customer_id)
        REFERENCES sales.customers(customer_id)
    );
    CREATE TABLE sales.order_items (
      order_id BIGINT,
      line_id INT,
      product_id BIGINT,
      CONSTRAINT fk_items_order FOREIGN KEY (order_id, line_id)
        REFERENCES sales.orders(order_id, line_id)
    )
    """

    contract = parse_ddl(ddl, dialect="databricks")

    customers = contract.tables["sales.customers"]
    orders = contract.tables["sales.orders"]
    items = contract.tables["sales.order_items"]
    assert customers.foreign_keys[0].parent_table == "sales.customers"
    assert orders.primary_key_columns == ("order_id", "line_id")
    assert len(orders.foreign_keys) == 2
    assert orders.foreign_keys[0].on_delete == "CASCADE"
    assert items.foreign_keys[0].child_columns == ("order_id", "line_id")
    assert items.foreign_keys[0].parent_columns == ("order_id", "line_id")


def test_parse_quoted_identifiers_preserves_case_and_spaces():
    contract = parse_ddl(
        "CREATE TABLE `Sales Schema`.`Customer Master` (`Customer ID` BIGINT PRIMARY KEY, `Full Name` STRING)",
        dialect="databricks",
    )

    table = contract.tables["Sales Schema.Customer Master"]

    assert table.name == "Customer Master"
    assert table.namespace == "Sales Schema"
    assert table.column_names() == ["Customer ID", "Full Name"]
    assert table.primary_key_columns == ("Customer ID",)


@pytest.mark.parametrize(
    ("ddl_type", "expected"),
    [
        ("INT", "int"),
        ("BIGINT", "bigint"),
        ("STRING", "string"),
        ("DOUBLE", "double"),
        ("BOOLEAN", "boolean"),
        ("DATE", "date"),
        ("TIMESTAMP_NTZ", "timestamp"),
        ("BINARY", "binary"),
    ],
)
def test_databricks_scalar_type_mapping(ddl_type: str, expected: str):
    contract = parse_ddl(f"CREATE TABLE typed_values (value {ddl_type})", dialect="databricks")

    assert contract.tables["typed_values"].columns[0].dtype == expected


def test_databricks_storage_properties_are_preserved_as_metadata():
    contract = parse_ddl(
        "CREATE TABLE lake.events (event_id BIGINT, event_date DATE) "
        "USING DELTA PARTITIONED BY (event_date)",
        dialect="databricks",
    )

    metadata = contract.tables["lake.events"].metadata

    assert metadata["storage_format"] == "DELTA"
    assert metadata["partitioned_by"] == ("event_date",)


def test_malformed_ddl_raises_structured_diagnostic():
    with pytest.raises(ContractParseError) as exc:
        parse_ddl("CREATE TABLE bad_table (id)")

    assert exc.value.diagnostics[0].construct == "missing_type"
    assert exc.value.diagnostics[0].severity == "error"


def test_unsupported_identity_strict_mode_fails_and_permissive_mode_warns():
    ddl = "CREATE TABLE t (id BIGINT GENERATED ALWAYS AS IDENTITY, name STRING)"

    with pytest.raises(ContractParseError) as exc:
        parse_ddl(ddl, dialect="databricks", strict=True)

    assert exc.value.diagnostics[0].construct == "GeneratedAsIdentityColumnConstraint"

    result = SQLDDLParser().parse(ddl, dialect="databricks", strict=False)

    assert result.warnings[0].construct == "GeneratedAsIdentityColumnConstraint"
    assert result.contract.metadata["diagnostics"][0]["severity"] == "warning"


def test_unsupported_type_fails_even_in_permissive_mode():
    with pytest.raises(ContractParseError) as exc:
        parse_ddl("CREATE TABLE shapes (shape GEOGRAPHY)", strict=False)

    assert exc.value.diagnostics[0].construct == "unsupported_type"


def test_compact_ddl_regression_remains_single_table_schema():
    table = table_schema_from_ddl("id int, name string")
    frame = generate_from_schema("id int, name string", rows=3, seed=7, realism="placeholder")

    assert table.column_names() == ["id", "name"]
    assert list(frame.columns) == ["id", "name"]
    assert frame.shape == (3, 2)


def test_full_create_table_ddl_generates_one_pandas_dataframe_with_semantics():
    contract = parse_ddl(
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

    first = generate_from_schema(contract, rows=5, seed=42)
    second = generate_from_schema(contract, rows=5, seed=42)
    plan = explain_generation_plan(contract)
    report = validate_generated_data(first, schema=contract)

    assert isinstance(first, pd.DataFrame)
    assert first.equals(second)
    assert list(first.columns) == ["customer_id", "customer_name", "email", "signup_date"]
    assert first["customer_id"].is_unique
    assert plan["fields"][1]["semantic_type"] == "customer_name"
    assert report["passed"] is True


def test_multi_table_contract_can_generate_existing_simple_relationships():
    ddl = """
        CREATE TABLE customers (customer_id BIGINT PRIMARY KEY, customer_name STRING);
        CREATE TABLE orders (
          order_id BIGINT PRIMARY KEY,
          customer_id BIGINT NOT NULL,
          order_amount DECIMAL(10,2),
          FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
        """
    contract = parse_ddl(ddl)

    data = generate_from_schema(
        contract, rows={"customers": 4, "orders": 10}, realism="placeholder"
    )

    assert set(data) == {"customers", "orders"}
    assert set(data["orders"]["customer_id"]).issubset(set(data["customers"]["customer_id"]))


def test_noop_advisor_plan_accepts_contract_schema():
    contract = parse_ddl("CREATE TABLE customers (customer_id BIGINT PRIMARY KEY, email STRING)")

    plan = infer_generation_plan(contract)

    assert plan.advisor == "none"
    assert [column.column for column in plan.columns] == [
        "customers.customer_id",
        "customers.email",
    ]
