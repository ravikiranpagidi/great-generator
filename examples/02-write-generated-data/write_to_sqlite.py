"""Write Pandas data to a local SQLite database. Requires SQLAlchemy."""

from sqlalchemy import create_engine

from great_generator import generate_from_schema

df = generate_from_schema({"customer_id": "string", "customer_name": "string"}, rows=100)
engine = create_engine("sqlite:///synthetic_data.db")
df.to_sql("synthetic_customers", engine, if_exists="replace", index=False)
