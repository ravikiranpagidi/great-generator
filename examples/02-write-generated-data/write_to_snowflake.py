"""Write Pandas data through SQLAlchemy. Install and configure the Snowflake connector."""

import os

from sqlalchemy import create_engine

from great_generator import generate_from_schema

df = generate_from_schema({"customer_id": "string", "customer_name": "string"}, rows=100)
engine = create_engine(os.environ["SNOWFLAKE_SQLALCHEMY_URL"])
df.to_sql("SYNTHETIC_CUSTOMERS", engine, if_exists="replace", index=False)
