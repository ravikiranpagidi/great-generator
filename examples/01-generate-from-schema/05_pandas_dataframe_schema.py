"""Use an empty Pandas DataFrame as the schema source and preserve its dtypes."""

import pandas as pd

from great_generator import generate_from_schema

empty = pd.DataFrame(
    {
        "claim_id": pd.Series(dtype="string"),
        "member_name": pd.Series(dtype="string"),
        "claim_amount": pd.Series(dtype="float64"),
        "submitted_at": pd.Series(dtype="datetime64[ns]"),
        "claim_status": pd.Series(dtype="string"),
    }
)

df = generate_from_schema(empty, rows=1000, domain="insurance")
print(df.head())
df.to_parquet("synthetic_claims.parquet", index=False)
