"""Optional Spark execution engine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from enterprise_synth.anomalies.injector import inject_anomalies_spark
from enterprise_synth.relationships.graph import topological_sort
from enterprise_synth.schemas.models import ColumnSpec, DomainSchema


def _require_spark(spark: Any) -> None:
    if spark is None:
        raise ValueError("Spark generation requires a SparkSession via spark=...")
    try:
        import pyspark  # noqa: F401
    except ImportError as exc:
        raise ImportError("Spark support requires: pip install enterprise-synth[spark]") from exc


def _rand(seed: int | None, salt: int) -> int:
    return int((seed or 0) + salt)


def _generic_value(column: ColumnSpec, key_column: str, seed: int | None, salt: int) -> Any:
    from pyspark.sql import functions as F

    dtype = column.dtype.lower()
    key = F.col(key_column)
    if "bool" in dtype:
        return F.rand(_rand(seed, salt)) < 0.5
    if "timestamp" in dtype or "datetime" in dtype:
        return F.to_timestamp(
            F.date_add(F.lit("2025-01-01"), F.pmod(F.xxhash64(key), F.lit(365)).cast("int"))
        )
    if dtype == "date" or dtype.endswith("date"):
        return F.date_add(F.lit("2025-01-01"), F.pmod(F.xxhash64(key), F.lit(365)).cast("int"))
    if "decimal" in dtype or "double" in dtype or "float" in dtype or "real" in dtype:
        if "score" in column.name:
            return F.round(F.rand(_rand(seed, salt)), 3)
        if any(token in column.name for token in ("amount", "cost", "price", "fee", "mrr")):
            return F.round(F.rand(_rand(seed, salt)) * 900 + 10, 2)
        return F.round(F.rand(_rand(seed, salt)) * 100, 2)
    if "int" in dtype or "long" in dtype:
        if "quantity" in column.name or "count" in column.name or "seats" in column.name:
            return F.pmod(F.xxhash64(key, F.lit(salt)), F.lit(100)) + F.lit(1)
        if "age" in column.name:
            return F.pmod(F.xxhash64(key, F.lit(salt)), F.lit(80)) + F.lit(1)
        return F.pmod(F.xxhash64(key, F.lit(salt)), F.lit(1000))
    return F.concat(F.lit(f"{column.name}_"), F.format_string("%08d", key))


def _generate_schema_driven(
    schema: DomainSchema,
    row_counts: Mapping[str, int],
    spark: Any,
    seed: int | None,
) -> dict[str, Any]:
    from pyspark.sql import functions as F

    generated: dict[str, Any] = {}
    order = topological_sort(schema.dependencies())
    salt = 100

    for table_name in order:
        table = schema.tables[table_name]
        count = int(row_counts[table_name])
        key_column = table.primary_key or "_row_id"
        frame = spark.range(1, count + 1).withColumnRenamed("id", key_column)

        for column in table.columns:
            if column.name == key_column:
                continue
            foreign_key = next((fk for fk in table.foreign_keys if fk.column == column.name), None)
            if foreign_key is not None:
                parent_count = int(row_counts[foreign_key.parent_table])
                if parent_count <= 0:
                    frame = frame.withColumn(column.name, F.lit(None))
                else:
                    frame = frame.withColumn(
                        column.name,
                        F.pmod(F.xxhash64(F.col(key_column), F.lit(salt)), F.lit(parent_count))
                        + F.lit(1),
                    )
            else:
                frame = frame.withColumn(
                    column.name, _generic_value(column, key_column, seed, salt)
                )
            salt += 1

        if table.primary_key is None and "_row_id" not in table.column_names():
            frame = frame.drop("_row_id")
        generated[table_name] = frame

    return generated


def _generate_ecommerce(
    row_counts: Mapping[str, int], spark: Any, seed: int | None
) -> dict[str, Any]:
    from pyspark.sql import functions as F

    customer_count = row_counts["customers"]
    product_count = row_counts["products"]
    order_count = row_counts["orders"]

    customers = (
        spark.range(1, customer_count + 1)
        .withColumnRenamed("id", "customer_id")
        .withColumn("customer_code", F.format_string("CUST%08d", F.col("customer_id")))
        .withColumn(
            "customer_segment",
            F.when(F.rand(_rand(seed, 1)) < 0.08, "vip")
            .when(F.rand(_rand(seed, 2)) < 0.22, "new")
            .when(F.rand(_rand(seed, 3)) < 0.10, "inactive")
            .otherwise("standard"),
        )
        .withColumn(
            "customer_status",
            F.when(F.col("customer_segment") == "inactive", "inactive").otherwise("active"),
        )
        .withColumn(
            "signup_date",
            F.date_add(
                F.lit("2023-01-01"), F.pmod(F.xxhash64("customer_id"), F.lit(1095)).cast("int")
            ),
        )
        .withColumn(
            "country",
            F.when(F.rand(_rand(seed, 4)) < 0.48, "US")
            .when(F.rand(_rand(seed, 5)) < 0.60, "GB")
            .when(F.rand(_rand(seed, 6)) < 0.77, "IN")
            .otherwise("CA"),
        )
        .withColumn("age", F.pmod(F.xxhash64("customer_id"), F.lit(58)) + F.lit(18))
    )

    products = (
        spark.range(1, product_count + 1)
        .withColumnRenamed("id", "product_id")
        .withColumn("sku", F.format_string("SKU%07d", F.col("product_id")))
        .withColumn(
            "category",
            F.when(F.pmod(F.xxhash64("product_id"), F.lit(100)) < 18, "electronics")
            .when(F.pmod(F.xxhash64("product_id"), F.lit(100)) < 42, "apparel")
            .when(F.pmod(F.xxhash64("product_id"), F.lit(100)) < 60, "home")
            .when(F.pmod(F.xxhash64("product_id"), F.lit(100)) < 72, "beauty")
            .when(F.pmod(F.xxhash64("product_id"), F.lit(100)) < 84, "sports")
            .otherwise("grocery"),
        )
        .withColumn(
            "brand",
            F.when(F.pmod(F.xxhash64("product_id"), F.lit(5)) == 0, "Northstar")
            .when(F.pmod(F.xxhash64("product_id"), F.lit(5)) == 1, "Aster")
            .when(F.pmod(F.xxhash64("product_id"), F.lit(5)) == 2, "Harbor")
            .when(F.pmod(F.xxhash64("product_id"), F.lit(5)) == 3, "Nimbus")
            .otherwise("Keystone"),
        )
        .withColumn(
            "list_price",
            F.round(
                F.when(F.col("category") == "electronics", F.rand(_rand(seed, 11)) * 700 + 30)
                .when(F.col("category") == "apparel", F.rand(_rand(seed, 12)) * 160 + 12)
                .when(F.col("category") == "home", F.rand(_rand(seed, 13)) * 260 + 20)
                .when(F.col("category") == "beauty", F.rand(_rand(seed, 14)) * 90 + 8)
                .when(F.col("category") == "sports", F.rand(_rand(seed, 15)) * 220 + 15)
                .otherwise(F.rand(_rand(seed, 16)) * 45 + 2),
                2,
            ),
        )
        .withColumn("active", F.rand(_rand(seed, 17)) > 0.03)
    )

    hot_customer_count = max(1, int(customer_count * 0.2))
    orders = (
        spark.range(1, order_count + 1)
        .withColumnRenamed("id", "order_id")
        .withColumn(
            "customer_id",
            F.when(
                F.rand(_rand(seed, 21)) < 0.62,
                F.pmod(F.xxhash64("order_id"), F.lit(hot_customer_count)) + F.lit(1),
            ).otherwise(
                F.pmod(F.xxhash64("order_id", F.lit(seed or 0)), F.lit(customer_count)) + F.lit(1)
            ),
        )
        .withColumn(
            "order_ts",
            F.to_timestamp(
                F.date_add(
                    F.lit("2025-01-01"), F.pmod(F.xxhash64("order_id"), F.lit(365)).cast("int")
                )
            ),
        )
        .withColumn("event_date", F.to_date("order_ts"))
        .withColumn(
            "order_status",
            F.when(F.rand(_rand(seed, 22)) < 0.04, "cancelled")
            .when(F.rand(_rand(seed, 23)) < 0.12, "pending")
            .otherwise("completed"),
        )
    )

    order_items = (
        spark.range(1, row_counts["order_items"] + 1)
        .withColumnRenamed("id", "order_item_id")
        .withColumn("order_id", F.pmod(F.xxhash64("order_item_id"), F.lit(order_count)) + F.lit(1))
        .withColumn(
            "product_id",
            F.pmod(F.xxhash64("order_item_id", F.lit(7)), F.lit(product_count)) + F.lit(1),
        )
        .join(products.select("product_id", "list_price"), on="product_id", how="left")
        .withColumn("quantity", F.pmod(F.xxhash64("order_item_id", F.lit(8)), F.lit(4)) + F.lit(1))
        .withColumn("unit_price", F.col("list_price"))
        .withColumn(
            "discount_amount",
            F.round(
                F.col("unit_price")
                * F.col("quantity")
                * F.when(F.rand(_rand(seed, 24)) < 0.25, 0.1).otherwise(0.0),
                2,
            ),
        )
        .withColumn(
            "line_amount",
            F.round(F.col("unit_price") * F.col("quantity") - F.col("discount_amount"), 2),
        )
        .drop("list_price")
    )
    subtotals = order_items.groupBy("order_id").agg(
        F.round(F.sum("line_amount"), 2).alias("subtotal")
    )
    orders = (
        orders.join(subtotals, on="order_id", how="left")
        .fillna({"subtotal": 0.0})
        .withColumn("tax", F.round(F.col("subtotal") * 0.0825, 2))
        .withColumn("shipping_fee", F.when(F.col("subtotal") >= 75, 0.0).otherwise(6.99))
        .withColumn(
            "total_amount", F.round(F.col("subtotal") + F.col("tax") + F.col("shipping_fee"), 2)
        )
    )

    payments = (
        spark.range(1, row_counts["payments"] + 1)
        .withColumnRenamed("id", "payment_id")
        .withColumn("order_id", F.pmod(F.xxhash64("payment_id"), F.lit(order_count)) + F.lit(1))
        .join(orders.select("order_id", "order_ts", "total_amount"), on="order_id", how="left")
        .withColumn("payment_ts", F.col("order_ts"))
        .withColumn(
            "payment_method",
            F.when(F.rand(_rand(seed, 25)) < 0.68, "card")
            .when(F.rand(_rand(seed, 26)) < 0.86, "wallet")
            .otherwise("bank_transfer"),
        )
        .withColumn(
            "payment_status", F.when(F.rand(_rand(seed, 27)) < 0.03, "failed").otherwise("captured")
        )
        .withColumn("amount", F.col("total_amount"))
        .withColumn("refunded_amount", F.lit(0.0))
        .drop("order_ts", "total_amount")
    )
    shipments = (
        spark.range(1, row_counts["shipments"] + 1)
        .withColumnRenamed("id", "shipment_id")
        .withColumn("order_id", F.pmod(F.xxhash64("shipment_id"), F.lit(order_count)) + F.lit(1))
        .join(orders.select("order_id", "order_ts"), on="order_id", how="left")
        .withColumn("shipment_ts", F.col("order_ts"))
        .withColumn("delayed", F.rand(_rand(seed, 28)) < 0.09)
        .withColumn(
            "delivery_ts",
            F.when(F.col("delayed"), F.date_add(F.to_date("order_ts"), 8)).otherwise(
                F.date_add(F.to_date("order_ts"), 4)
            ),
        )
        .withColumn(
            "carrier",
            F.when(F.rand(_rand(seed, 29)) < 0.34, "UPS")
            .when(F.rand(_rand(seed, 30)) < 0.62, "FedEx")
            .when(F.rand(_rand(seed, 31)) < 0.88, "USPS")
            .otherwise("DHL"),
        )
        .withColumn("shipment_status", F.when(F.col("delayed"), "delayed").otherwise("delivered"))
        .drop("order_ts")
    )
    returns = (
        spark.range(1, row_counts["returns"] + 1)
        .withColumnRenamed("id", "return_id")
        .withColumn("order_id", F.pmod(F.xxhash64("return_id"), F.lit(order_count)) + F.lit(1))
        .join(orders.select("order_id", "order_ts", "total_amount"), on="order_id", how="left")
        .withColumn("return_ts", F.date_add(F.to_date("order_ts"), 7))
        .withColumn(
            "return_reason",
            F.when(F.rand(_rand(seed, 32)) < 0.30, "size_issue")
            .when(F.rand(_rand(seed, 33)) < 0.52, "damaged")
            .otherwise("changed_mind"),
        )
        .withColumn(
            "return_status",
            F.when(F.rand(_rand(seed, 34)) < 0.06, "rejected").otherwise("approved"),
        )
        .withColumn("refund_amount", F.col("total_amount"))
        .drop("order_ts", "total_amount")
    )
    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
        "shipments": shipments,
        "returns": returns,
    }


def _generate_banking(
    row_counts: Mapping[str, int], spark: Any, seed: int | None
) -> dict[str, Any]:
    from pyspark.sql import functions as F

    customer_count = row_counts["customers"]
    account_count = row_counts["accounts"]
    card_count = row_counts["cards"]
    merchant_count = row_counts["merchants"]
    transaction_count = row_counts["transactions"]

    customers = (
        spark.range(1, customer_count + 1)
        .withColumnRenamed("id", "customer_id")
        .withColumn("customer_code", F.format_string("CUS%08d", F.col("customer_id")))
        .withColumn(
            "customer_type",
            F.when(F.rand(_rand(seed, 41)) < 0.16, "business").otherwise("individual"),
        )
        .withColumn(
            "segment",
            F.when(
                F.col("customer_type") == "business",
                F.when(F.rand(_rand(seed, 42)) < 0.18, "enterprise").otherwise("smb"),
            )
            .when(F.rand(_rand(seed, 43)) < 0.22, "premium")
            .otherwise("mass"),
        )
        .withColumn(
            "opened_date",
            F.date_add(
                F.lit("2020-01-01"), F.pmod(F.xxhash64("customer_id"), F.lit(2190)).cast("int")
            ),
        )
        .withColumn(
            "status",
            F.when(F.rand(_rand(seed, 44)) < 0.03, "closed")
            .when(F.rand(_rand(seed, 45)) < 0.11, "dormant")
            .otherwise("active"),
        )
        .withColumn(
            "risk_band",
            F.when(F.rand(_rand(seed, 46)) < 0.04, "high")
            .when(F.rand(_rand(seed, 47)) < 0.26, "medium")
            .otherwise("low"),
        )
        .withColumn(
            "region",
            F.when(F.pmod(F.xxhash64("customer_id"), F.lit(4)) == 0, "northeast")
            .when(F.pmod(F.xxhash64("customer_id"), F.lit(4)) == 1, "south")
            .when(F.pmod(F.xxhash64("customer_id"), F.lit(4)) == 2, "midwest")
            .otherwise("west"),
        )
    )
    accounts = (
        spark.range(1, account_count + 1)
        .withColumnRenamed("id", "account_id")
        .withColumn(
            "customer_id", F.pmod(F.xxhash64("account_id"), F.lit(customer_count)) + F.lit(1)
        )
        .withColumn(
            "account_type",
            F.when(F.pmod(F.xxhash64("account_id"), F.lit(100)) < 42, "checking")
            .when(F.pmod(F.xxhash64("account_id"), F.lit(100)) < 70, "savings")
            .when(F.pmod(F.xxhash64("account_id"), F.lit(100)) < 90, "credit")
            .otherwise("business_checking"),
        )
        .withColumn(
            "opened_date",
            F.date_add(
                F.lit("2020-01-01"), F.pmod(F.xxhash64("account_id"), F.lit(2190)).cast("int")
            ),
        )
        .withColumn("balance", F.round(F.rand(_rand(seed, 48)) * 50_000 + 100, 2))
        .withColumn(
            "status",
            F.when(F.rand(_rand(seed, 49)) < 0.03, "closed")
            .when(F.rand(_rand(seed, 50)) < 0.07, "restricted")
            .otherwise("open"),
        )
    )
    cards = (
        spark.range(1, card_count + 1)
        .withColumnRenamed("id", "card_id")
        .withColumn("customer_id", F.pmod(F.xxhash64("card_id"), F.lit(customer_count)) + F.lit(1))
        .withColumn(
            "card_type",
            F.when(F.rand(_rand(seed, 51)) < 0.60, "debit")
            .when(F.rand(_rand(seed, 52)) < 0.93, "credit")
            .otherwise("corporate"),
        )
        .withColumn(
            "issued_date",
            F.date_add(F.lit("2021-01-01"), F.pmod(F.xxhash64("card_id"), F.lit(1825)).cast("int")),
        )
        .withColumn(
            "status",
            F.when(F.rand(_rand(seed, 53)) < 0.03, "blocked")
            .when(F.rand(_rand(seed, 54)) < 0.06, "expired")
            .otherwise("active"),
        )
    )
    merchants = (
        spark.range(1, merchant_count + 1)
        .withColumnRenamed("id", "merchant_id")
        .withColumn("merchant_name", F.format_string("Merchant %05d", F.col("merchant_id")))
        .withColumn(
            "merchant_category",
            F.when(F.pmod(F.xxhash64("merchant_id"), F.lit(100)) < 22, "grocery")
            .when(F.pmod(F.xxhash64("merchant_id"), F.lit(100)) < 34, "fuel")
            .when(F.pmod(F.xxhash64("merchant_id"), F.lit(100)) < 44, "travel")
            .when(F.pmod(F.xxhash64("merchant_id"), F.lit(100)) < 62, "restaurant")
            .when(F.pmod(F.xxhash64("merchant_id"), F.lit(100)) < 82, "ecommerce")
            .when(F.pmod(F.xxhash64("merchant_id"), F.lit(100)) < 94, "utilities")
            .otherwise("cash_like"),
        )
        .withColumn(
            "risk_band", F.when(F.col("merchant_category") == "cash_like", "high").otherwise("low")
        )
    )
    transactions = (
        spark.range(1, transaction_count + 1)
        .withColumnRenamed("id", "transaction_id")
        .withColumn(
            "account_id", F.pmod(F.xxhash64("transaction_id"), F.lit(account_count)) + F.lit(1)
        )
        .withColumn(
            "card_id",
            F.when(
                F.rand(_rand(seed, 55)) < 0.67,
                F.pmod(F.xxhash64("transaction_id", F.lit(3)), F.lit(card_count)) + F.lit(1),
            ),
        )
        .withColumn(
            "merchant_id",
            F.pmod(F.xxhash64("transaction_id", F.lit(4)), F.lit(merchant_count)) + F.lit(1),
        )
        .withColumn(
            "transaction_ts",
            F.to_timestamp(
                F.date_add(
                    F.lit("2025-01-01"),
                    F.pmod(F.xxhash64("transaction_id"), F.lit(365)).cast("int"),
                )
            ),
        )
        .withColumn("event_date", F.to_date("transaction_ts"))
        .withColumn("ingestion_timestamp", F.col("transaction_ts"))
        .withColumn(
            "transaction_type",
            F.when(F.rand(_rand(seed, 56)) < 0.66, "card_purchase")
            .when(F.rand(_rand(seed, 57)) < 0.78, "ach_credit")
            .when(F.rand(_rand(seed, 58)) < 0.86, "atm_withdrawal")
            .otherwise("transfer"),
        )
        .withColumn(
            "direction",
            F.when(F.col("transaction_type") == "ach_credit", "credit").otherwise("debit"),
        )
        .withColumn("amount", F.round(F.rand(_rand(seed, 59)) * 900 + 5, 2))
        .withColumn(
            "status",
            F.when(F.rand(_rand(seed, 60)) < 0.02, "reversed")
            .when(F.rand(_rand(seed, 61)) < 0.06, "pending")
            .otherwise("posted"),
        )
        .withColumn("is_late_arriving", F.lit(False))
        .withColumn("duplicate_record", F.lit(False))
    )
    fraud_events = (
        spark.range(1, row_counts["fraud_events"] + 1)
        .withColumnRenamed("id", "fraud_event_id")
        .withColumn(
            "transaction_id",
            F.pmod(F.xxhash64("fraud_event_id"), F.lit(transaction_count)) + F.lit(1),
        )
        .withColumn("event_ts", F.current_timestamp())
        .withColumn(
            "fraud_type",
            F.when(F.rand(_rand(seed, 62)) < 0.25, "card_testing")
            .when(F.rand(_rand(seed, 63)) < 0.55, "account_takeover")
            .otherwise("velocity_spike"),
        )
        .withColumn("risk_score", F.round(F.rand(_rand(seed, 64)) * 0.27 + 0.72, 3))
        .withColumn(
            "status",
            F.when(F.rand(_rand(seed, 65)) < 0.10, "dismissed")
            .when(F.rand(_rand(seed, 66)) < 0.42, "review")
            .otherwise("confirmed"),
        )
    )
    cdc_customer_changes = (
        spark.range(1, row_counts["cdc_customer_changes"] + 1)
        .withColumnRenamed("id", "sequence_number")
        .withColumn(
            "customer_id", F.pmod(F.xxhash64("sequence_number"), F.lit(customer_count)) + F.lit(1)
        )
        .withColumn(
            "operation",
            F.when(F.rand(_rand(seed, 67)) < 0.34, "insert")
            .when(F.rand(_rand(seed, 68)) < 0.75, "update")
            .otherwise("delete"),
        )
        .withColumn(
            "before", F.when(F.col("operation") == "insert", F.lit(None)).otherwise(F.lit("{}"))
        )
        .withColumn(
            "after", F.when(F.col("operation") == "delete", F.lit(None)).otherwise(F.lit("{}"))
        )
        .withColumn("event_timestamp", F.current_timestamp())
        .withColumn("ingestion_timestamp", F.current_timestamp())
        .withColumn("source_system", F.lit("core_banking"))
        .withColumn("late_arriving", F.lit(False))
        .withColumn("duplicate", F.lit(False))
    )
    return {
        "customers": customers,
        "accounts": accounts,
        "transactions": transactions,
        "cards": cards,
        "merchants": merchants,
        "fraud_events": fraud_events,
        "cdc_customer_changes": cdc_customer_changes,
    }


def generate_domain(
    domain: str,
    schema: DomainSchema,
    row_counts: Mapping[str, int],
    spark: Any,
    seed: int | None,
    anomalies: Mapping[str, float] | None,
) -> dict[str, Any]:
    _require_spark(spark)
    if domain == "ecommerce":
        data = _generate_ecommerce(row_counts, spark, seed)
    elif domain == "banking":
        data = _generate_banking(row_counts, spark, seed)
    else:
        data = _generate_schema_driven(schema, row_counts, spark, seed)
    return inject_anomalies_spark(data, schema, anomalies, seed=seed)
