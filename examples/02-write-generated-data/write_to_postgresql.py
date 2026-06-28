"""Write Pandas data to PostgreSQL using a secret-backed SQLAlchemy URL."""

import os

from sqlalchemy import create_engine

from great_generator import generate_from_schema

df = generate_from_schema({"customer_id": "string", "customer_name": "string"}, rows=100)
engine = create_engine(os.environ["POSTGRESQL_SQLALCHEMY_URL"])
df.to_sql("synthetic_customers", engine, if_exists="replace", index=False)
