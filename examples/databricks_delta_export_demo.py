"""Databricks or Spark Delta export demo.

Run this in a Spark environment with Delta support configured.
"""

from great_generator import generate_domain

data = generate_domain(
    "banking",
    engine="spark",
    scale="large",
    realism="realistic",
    output_path="/mnt/demo/great_generator/banking_delta",
    output_format="delta",
    partition_by=["event_date"],
)

transactions = data["transactions"]
transactions.printSchema()
transactions.show(5, truncate=False)
