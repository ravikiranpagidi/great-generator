# Databricks / PySpark usage pattern for the retail star-schema example.
# Paste the relevant cells into a Databricks notebook after installing the package:
#   %pip install great-generator
#
# This file is an example, not a test. The same DataFrame-first pattern works in
# Databricks, local PySpark, Microsoft Fabric Spark, EMR, Glue, Synapse Spark,
# and any Spark runtime where pandas-to-Spark conversion is acceptable for the
# chosen row counts. For very large datasets, prefer Spark-native generation or
# generate/write in chunks.

# If this file lives with the repository checkout, load the local example module.
# In a notebook, replace this with your preferred import pattern.
import importlib.util
from pathlib import Path

from great_generator import export_data

example_path = Path("examples/06-retail-star-schema/generate.py")
spec = importlib.util.spec_from_file_location("retail_star_generate", example_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

pandas_tables = module.generate_dataset(
    rows={
        "dim_customer": 1000,
        "dim_product": 250,
        "dim_store": 50,
        "dim_date": 365,
        "fact_sales": 25000,
    },
    seed=2026,
)

spark_session = globals().get("spark")
if spark_session is None:
    raise RuntimeError("This example expects a Spark notebook/runtime with a `spark` session.")

spark_tables = {name: spark_session.createDataFrame(frame) for name, frame in pandas_tables.items()}

# Databricks local filesystem / DBFS-style path
export_data(
    spark_tables,
    output_path="dbfs:/tmp/great-generator/retail_star_schema",
    output_format="parquet",
    engine="spark",
    mode="overwrite",
)

# Delta Lake path if Delta is installed/configured in the runtime
export_data(
    spark_tables,
    output_path="dbfs:/tmp/great-generator/retail_star_schema_delta",
    output_format="delta",
    engine="spark",
    mode="overwrite",
)

# Or keep complete control with native Spark writes.
for table_name, frame in spark_tables.items():
    frame.write.mode("overwrite").format("delta").saveAsTable(f"demo_retail.{table_name}")
