"""Use Great Generator's typed TableSchema for library extensions."""

from great_generator import generate_from_schema
from great_generator.schemas.models import ColumnSpec, TableSchema

schema = TableSchema(
    name="products",
    columns=(
        ColumnSpec("product_id", "string", nullable=False),
        ColumnSpec("product_name", "string"),
        ColumnSpec("category", "string"),
        ColumnSpec("unit_price", "double"),
    ),
    primary_key="product_id",
)

df = generate_from_schema(schema, rows=500, domain="retail")
print(df.head())
df.to_json("synthetic_products.json", orient="records", lines=True)
