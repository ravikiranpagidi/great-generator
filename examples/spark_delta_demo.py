from enterprise_synth import generate_domain

# spark must already be a configured SparkSession
generate_domain(
    "banking",
    engine="spark",
    scale="large",
    spark=spark,  # noqa: F821 - assume an existing SparkSession in notebook/demo contexts
    output_path="/mnt/demo/banking_delta",
    output_format="delta",
    partition_by=["event_date"],
    seed=42,
)
