"""Generate data from a Pandas dtype mapping in a notebook or local workflow."""

import pandas as pd

from great_generator import generate_from_schema

sample = pd.DataFrame(
    {
        "employee_id": pd.Series(dtype="string"),
        "employee_name": pd.Series(dtype="string"),
        "employee_age": pd.Series(dtype="int64"),
        "salary": pd.Series(dtype="float64"),
        "hire_date": pd.Series(dtype="datetime64[ns]"),
    }
)

df = generate_from_schema(sample.dtypes.to_dict(), rows=500, domain="hr")
print(df.head())
df.to_csv("synthetic_employees.csv", index=False)
