"""Generate a realistic retail star schema from SQL DDL.

Run from the repository root:

    python examples/06-retail-star-schema/generate.py

The example returns a dictionary of pandas DataFrames, validates primary-key and
foreign-key integrity, and optionally writes table-per-folder outputs plus a
manifest. It is intentionally DataFrame-first: you can use the returned frames in
Pandas, convert them to Spark, or write them to any destination your runtime
supports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from great_generator import export_data, generate_from_schema, parse_ddl
from great_generator.io import build_generation_manifest

EXAMPLE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = EXAMPLE_DIR / "schema.sql"
CONFIG_PATH = EXAMPLE_DIR / "generation.yml"

DEFAULT_ROWS = {
    "dim_customer": 1_000,
    "dim_product": 250,
    "dim_store": 50,
    "dim_date": 365,
    "fact_sales": 25_000,
}

CATEGORY_PRICE_RANGES = {
    "Electronics": (80.0, 950.0),
    "Home": (15.0, 250.0),
    "Grocery": (2.0, 80.0),
    "Fashion": (10.0, 220.0),
    "Beauty": (6.0, 160.0),
    "Sports": (12.0, 300.0),
}


def load_contract(schema_path: Path = SCHEMA_PATH):
    """Parse the retail SQL DDL into a canonical generation contract."""

    ddl_text = schema_path.read_text(encoding="utf-8").lstrip("\ufeff")
    return parse_ddl(
        ddl_text,
        dialect="databricks",
        strict=True,
        name="retail_star_schema",
    )


def generate_dataset(
    *,
    rows: dict[str, int] | None = None,
    seed: int | None = 2026,
    realism: str = "realistic",
) -> dict[str, pd.DataFrame]:
    """Generate and enrich the retail star-schema tables."""

    contract = load_contract()
    generated = generate_from_schema(
        contract,
        rows=rows or DEFAULT_ROWS,
        seed=seed,
        realism=realism,
    )
    if not isinstance(generated, dict):  # defensive guard for future API changes
        raise TypeError("Retail star schema generation should return a table dictionary.")
    return apply_retail_business_rules(generated, seed=seed)


def apply_retail_business_rules(
    data: dict[str, pd.DataFrame], *, seed: int | None = 2026
) -> dict[str, pd.DataFrame]:
    """Apply deterministic retail patterns without breaking relationships."""

    rng = np.random.default_rng(seed)
    enriched = {name: frame.copy() for name, frame in data.items()}

    customers = enriched["dim_customer"].sort_values("customer_key").reset_index(drop=True)
    segments = np.array(["New", "Standard", "Loyal", "VIP"])
    segment_probabilities = np.array([0.22, 0.48, 0.22, 0.08])
    customers["customer_id"] = customers["customer_key"].map(lambda value: f"CUST{value:06d}")
    customers["customer_segment"] = rng.choice(
        segments, size=len(customers), p=segment_probabilities
    )
    signup_start = pd.Timestamp("2023-01-01")
    customers["signup_date"] = signup_start + pd.to_timedelta(
        rng.integers(0, 1095, size=len(customers)), unit="D"
    )
    enriched["dim_customer"] = customers

    products = enriched["dim_product"].sort_values("product_key").reset_index(drop=True)
    categories = np.array(list(CATEGORY_PRICE_RANGES))
    category_probabilities = np.array([0.18, 0.18, 0.22, 0.19, 0.12, 0.11])
    products["product_id"] = products["product_key"].map(lambda value: f"SKU{value:06d}")
    products["category"] = rng.choice(categories, size=len(products), p=category_probabilities)
    products["product_name"] = [
        f"{category} Item {key:04d}"
        for category, key in zip(products["category"], products["product_key"])
    ]
    products["unit_price"] = [
        round(float(rng.uniform(*CATEGORY_PRICE_RANGES[category])), 2)
        for category in products["category"]
    ]
    enriched["dim_product"] = products

    stores = enriched["dim_store"].sort_values("store_key").reset_index(drop=True)
    regions = np.array(["Northeast", "Southeast", "Midwest", "Southwest", "West"])
    stores["store_id"] = stores["store_key"].map(lambda value: f"STORE{value:04d}")
    stores["region"] = rng.choice(regions, size=len(stores), p=[0.20, 0.22, 0.20, 0.16, 0.22])
    stores["store_name"] = [
        f"{region} Retail #{key:03d}" for region, key in zip(stores["region"], stores["store_key"])
    ]
    enriched["dim_store"] = stores

    dates = enriched["dim_date"].sort_values("date_key").reset_index(drop=True)
    dates["calendar_date"] = pd.date_range("2025-01-01", periods=len(dates), freq="D")
    dates["fiscal_year"] = dates["calendar_date"].dt.year
    dates["month_name"] = dates["calendar_date"].dt.month_name()
    enriched["dim_date"] = dates

    fact = enriched["fact_sales"].sort_values("sales_key").reset_index(drop=True)
    fact = _assign_weighted_foreign_keys(fact, customers, products, stores, dates, rng)
    fact = _recalculate_sales_amounts(fact, customers, products, dates, rng)
    enriched["fact_sales"] = fact

    return enriched


def _assign_weighted_foreign_keys(
    fact: pd.DataFrame,
    customers: pd.DataFrame,
    products: pd.DataFrame,
    stores: pd.DataFrame,
    dates: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    customer_weights = _pareto_like_weights(len(customers), top_share=0.20, top_weight=6.0)
    product_weights = _pareto_like_weights(len(products), top_share=0.15, top_weight=4.0)
    store_weights = _pareto_like_weights(len(stores), top_share=0.25, top_weight=3.0)

    date_weights = np.ones(len(dates), dtype=float)
    date_values = pd.to_datetime(dates["calendar_date"])
    date_weights[date_values.dt.dayofweek >= 5] *= 1.35
    date_weights[date_values.dt.month.isin([11, 12])] *= 1.60
    date_weights = date_weights / date_weights.sum()

    fact["customer_key"] = rng.choice(customers["customer_key"], size=len(fact), p=customer_weights)
    fact["product_key"] = rng.choice(products["product_key"], size=len(fact), p=product_weights)
    fact["store_key"] = rng.choice(stores["store_key"], size=len(fact), p=store_weights)
    fact["date_key"] = rng.choice(dates["date_key"], size=len(fact), p=date_weights)
    return fact


def _pareto_like_weights(count: int, *, top_share: float, top_weight: float) -> np.ndarray:
    weights = np.ones(count, dtype=float)
    top_count = max(1, int(count * top_share))
    weights[:top_count] = top_weight
    return weights / weights.sum()


def _recalculate_sales_amounts(
    fact: pd.DataFrame,
    customers: pd.DataFrame,
    products: pd.DataFrame,
    dates: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    product_lookup = products.set_index("product_key")[["unit_price", "category"]]
    customer_lookup = customers.set_index("customer_key")[["customer_segment"]]
    date_lookup = dates.set_index("date_key")[["calendar_date"]]

    fact = fact.join(product_lookup, on="product_key")
    fact = fact.join(customer_lookup, on="customer_key")
    fact = fact.join(date_lookup, on="date_key")

    base_quantity = rng.poisson(lam=1.8, size=len(fact)) + 1
    electronics_mask = fact["category"].eq("Electronics").to_numpy()
    base_quantity[electronics_mask] = np.minimum(base_quantity[electronics_mask], 3)
    fact["quantity"] = np.clip(base_quantity, 1, 8)

    discount_rate = np.select(
        [
            fact["customer_segment"].eq("VIP"),
            fact["customer_segment"].eq("Loyal"),
            fact["calendar_date"].dt.month.isin([11, 12]),
        ],
        [0.12, 0.08, 0.06],
        default=0.03,
    )
    gross_amount = fact["unit_price"] * fact["quantity"]
    fact["gross_amount"] = gross_amount.round(2)
    fact["discount_amount"] = (gross_amount * discount_rate).round(2)
    fact["net_amount"] = (fact["gross_amount"] - fact["discount_amount"]).round(2)

    return fact[
        [
            "sales_key",
            "customer_key",
            "product_key",
            "store_key",
            "date_key",
            "quantity",
            "gross_amount",
            "discount_amount",
            "net_amount",
        ]
    ]


def validate_dataset(data: dict[str, pd.DataFrame]) -> dict[str, bool]:
    """Validate the star schema for demo and CI usage."""

    checks = {
        "expected_tables_present": set(data) == set(DEFAULT_ROWS),
        "primary_keys_unique": True,
        "foreign_keys_valid": True,
        "fact_amounts_reconciled": True,
    }

    for table_name, key in {
        "dim_customer": "customer_key",
        "dim_product": "product_key",
        "dim_store": "store_key",
        "dim_date": "date_key",
        "fact_sales": "sales_key",
    }.items():
        frame = data[table_name]
        checks["primary_keys_unique"] = checks["primary_keys_unique"] and frame[key].is_unique
        checks["primary_keys_unique"] = checks["primary_keys_unique"] and frame[key].notna().all()

    fact = data["fact_sales"]
    for child_column, parent_table in {
        "customer_key": "dim_customer",
        "product_key": "dim_product",
        "store_key": "dim_store",
        "date_key": "dim_date",
    }.items():
        valid_parent_keys = set(data[parent_table][child_column])
        checks["foreign_keys_valid"] = checks["foreign_keys_valid"] and set(
            fact[child_column]
        ).issubset(valid_parent_keys)

    expected_net = (fact["gross_amount"] - fact["discount_amount"]).round(2)
    checks["fact_amounts_reconciled"] = bool(expected_net.equals(fact["net_amount"].round(2)))
    return {name: bool(value) for name, value in checks.items()}


def build_manifest(
    data: dict[str, pd.DataFrame], *, seed: int | None, rows: dict[str, int], realism: str
) -> dict[str, Any]:
    """Create an audit-friendly manifest for generated tables."""

    contract = load_contract()
    validation = validate_dataset(data)
    return build_generation_manifest(
        dataset_name="retail_star_schema",
        tables=data,
        engine="pandas",
        seed=seed,
        schema_fingerprint=contract.fingerprint(),
        parameters={"rows": rows, "realism": realism},
        validation=validation,
        real_data_ingested=False,
        warnings=[] if all(validation.values()) else ["One or more validation checks failed."],
    )


def load_generation_config(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load the small example YAML file without adding a PyYAML dependency."""

    if not config_path.exists():
        return {
            "dataset_name": "retail_star_schema",
            "engine": "pandas",
            "seed": 2026,
            "realism": "realistic",
            "rows": dict(DEFAULT_ROWS),
        }

    config: dict[str, Any] = {"rows": {}}
    section: str | None = None
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line:
            continue
        if ":" not in line:
            continue
        if line.startswith("  ") and section == "rows":
            key, value = line.strip().split(":", 1)
            config["rows"][key.strip()] = int(value.strip().replace("_", ""))
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "rows":
            section = "rows"
            continue
        section = None
        if key == "seed":
            config[key] = int(value)
        else:
            config[key] = value
    return config


def write_outputs(
    data: dict[str, pd.DataFrame], manifest: dict[str, Any], *, output_path: str, output_format: str
) -> Path:
    """Write table-per-folder data and a manifest file."""

    path = Path(output_path)
    if not path.is_absolute():
        path = EXAMPLE_DIR / path
    export_data(data, output_path=path, output_format=output_format, engine="pandas")
    path.mkdir(parents=True, exist_ok=True)
    (path / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def main() -> None:
    config = load_generation_config()
    rows = config.get("rows") or dict(DEFAULT_ROWS)
    seed = config.get("seed")
    realism = config.get("realism", "realistic")
    data = generate_dataset(rows=rows, seed=seed, realism=realism)
    validation = validate_dataset(data)
    if not all(validation.values()):
        raise RuntimeError(f"Retail star-schema validation failed: {validation}")

    manifest = build_manifest(data, seed=seed, rows=rows, realism=realism)
    output_path = write_outputs(
        data,
        manifest,
        output_path=config.get("output_path", "outputs/retail_star_schema"),
        output_format=config.get("output_format", "parquet"),
    )
    print(f"Generated retail star schema at {output_path}")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
