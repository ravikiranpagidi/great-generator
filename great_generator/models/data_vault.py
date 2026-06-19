"""Data Vault model generation for domain packs."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import pandas as pd

from great_generator.schemas.models import DomainSchema


def generate_data_vault_model(
    domain: str,
    source: Mapping[str, pd.DataFrame],
    schema: DomainSchema,
) -> dict[str, pd.DataFrame]:
    """Build hubs, links, and satellites from a generated domain dataset."""

    result: dict[str, pd.DataFrame] = {}
    load_date = pd.Timestamp("2025-01-01")
    record_source = f"great_generator.{domain}"

    for table_name, table in schema.tables.items():
        if table.primary_key is None or table_name not in source:
            continue
        frame = source[table_name]
        hub_name = f"hub_{_singular(table_name)}"
        hub_key = f"{hub_name}_key"
        result[hub_name] = pd.DataFrame(
            {
                hub_key: [
                    _hash_key(domain, table_name, value) for value in frame[table.primary_key]
                ],
                "business_key": frame[table.primary_key].astype(str).to_numpy(),
                "load_date": load_date,
                "record_source": record_source,
            }
        )

        attribute_columns = [
            column.name
            for column in table.columns
            if column.name != table.primary_key
            and column.name not in {foreign_key.column for foreign_key in table.foreign_keys}
        ]
        satellite = pd.DataFrame(
            {
                hub_key: [
                    _hash_key(domain, table_name, value) for value in frame[table.primary_key]
                ],
                "load_date": load_date,
                "record_source": record_source,
                "hashdiff": [
                    _hash_values([row[column] for column in attribute_columns])
                    for _, row in frame.iterrows()
                ],
            }
        )
        for column in attribute_columns:
            satellite[column] = frame[column].to_numpy()
        result[f"sat_{_singular(table_name)}_details"] = satellite

    for table_name, table in schema.tables.items():
        if table.primary_key is None or table_name not in source:
            continue
        frame = source[table_name]
        for foreign_key in table.foreign_keys:
            parent = schema.tables[foreign_key.parent_table]
            if parent.primary_key is None:
                continue
            child_hub = f"hub_{_singular(table_name)}"
            parent_hub = f"hub_{_singular(foreign_key.parent_table)}"
            child_hub_key = f"{child_hub}_key"
            parent_hub_key = f"{parent_hub}_key"
            link_name = f"link_{_singular(table_name)}_{_singular(foreign_key.parent_table)}"
            result[link_name] = pd.DataFrame(
                {
                    f"{link_name}_key": [
                        _hash_key(domain, link_name, child, parent_value)
                        for child, parent_value in zip(
                            frame[table.primary_key], frame[foreign_key.column]
                        )
                    ],
                    child_hub_key: [
                        _hash_key(domain, table_name, value) for value in frame[table.primary_key]
                    ],
                    parent_hub_key: [
                        _hash_key(domain, foreign_key.parent_table, value)
                        for value in frame[foreign_key.column]
                    ],
                    "load_date": load_date,
                    "record_source": record_source,
                }
            )

    result["_model_metadata"] = pd.DataFrame(
        [
            {
                "model_type": "data_vault",
                "domain": domain,
                "generated_by": "great-generator",
            }
        ]
    )
    return result


def _hash_key(*values: Any) -> str:
    return _hash_values(values)


def _hash_values(values: Any) -> str:
    joined = "|".join("" if pd.isna(value) else str(value) for value in values)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def _singular(name: str) -> str:
    if name.endswith("ies"):
        return f"{name[:-3]}y"
    if name.endswith("s"):
        return name[:-1]
    return name
