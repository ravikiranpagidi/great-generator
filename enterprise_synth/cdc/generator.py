"""CDC-style event simulation."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd

from enterprise_synth.utils.random import get_rng

DEFAULT_OPERATIONS = ("insert", "update", "delete")


def _serialize(record: pd.Series | None) -> str | None:
    if record is None:
        return None
    payload = {
        key: (value.isoformat() if hasattr(value, "isoformat") else value)
        for key, value in record.to_dict().items()
    }
    return json.dumps(payload, sort_keys=True)


def generate_customer_cdc(
    customers: pd.DataFrame,
    rows: int,
    operations: Sequence[str] | None = None,
    late_arrival_rate: float = 0.0,
    duplicate_rate: float = 0.0,
    seed: int | None = None,
) -> pd.DataFrame:
    """Generate CDC records from a banking customer dimension."""

    operations = tuple(operations or DEFAULT_OPERATIONS)
    invalid = set(operations) - set(DEFAULT_OPERATIONS)
    if invalid:
        raise ValueError(f"Unsupported CDC operation(s): {sorted(invalid)}")
    if rows < 0:
        raise ValueError("rows must be non-negative")
    if customers.empty and rows:
        raise ValueError("Cannot generate CDC events from an empty customer table.")

    rng = get_rng(seed, "cdc.customers")
    chosen_indices = (
        rng.choice(customers.index.to_numpy(), size=rows, replace=True)
        if rows
        else np.array([], dtype=int)
    )
    sampled = (
        customers.loc[chosen_indices].reset_index(drop=True) if rows else customers.head(0).copy()
    )
    chosen_operations = rng.choice(np.array(operations), size=rows, replace=True)

    event_dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    event_timestamp = (
        pd.to_datetime(rng.choice(event_dates.to_numpy(), size=rows, replace=True))
        + pd.to_timedelta(rng.integers(0, 24 * 60, size=rows), unit="m")
        if rows
        else pd.Series(dtype="datetime64[ns]")
    )
    late_arriving = rng.random(rows) < late_arrival_rate if rows else np.array([], dtype=bool)
    normal_delay = (
        pd.to_timedelta(rng.integers(0, 180, size=rows), unit="m") if rows else pd.to_timedelta([])
    )
    late_delay = (
        pd.to_timedelta(rng.integers(2, 8, size=rows), unit="D") if rows else pd.to_timedelta([])
    )
    ingestion_timestamp = event_timestamp + np.where(late_arriving, late_delay, normal_delay)

    before_values: list[str | None] = []
    after_values: list[str | None] = []
    for operation, (_, record) in zip(chosen_operations, sampled.iterrows()):
        if operation == "insert":
            before_values.append(None)
            after_values.append(_serialize(record))
        elif operation == "delete":
            before_values.append(_serialize(record))
            after_values.append(None)
        else:
            updated = record.copy()
            updated["status"] = "dormant" if record.get("status") == "active" else "active"
            updated["risk_band"] = rng.choice(["low", "medium", "high"], p=[0.70, 0.24, 0.06])
            before_values.append(_serialize(record))
            after_values.append(_serialize(updated))

    result = pd.DataFrame(
        {
            "customer_id": sampled["customer_id"].to_numpy() if rows else pd.Series(dtype="int64"),
            "operation": chosen_operations,
            "before": before_values,
            "after": after_values,
            "event_timestamp": pd.to_datetime(event_timestamp),
            "ingestion_timestamp": pd.to_datetime(ingestion_timestamp),
            "sequence_number": np.arange(1, rows + 1, dtype=np.int64),
            "source_system": rng.choice(
                ["crm", "core_banking", "mobile_app"], size=rows, p=[0.42, 0.48, 0.10]
            ),
            "late_arriving": late_arriving,
            "duplicate": False,
        }
    )

    duplicate_count = int(round(rows * duplicate_rate))
    if duplicate_count:
        duplicate_rows = result.sample(
            n=duplicate_count, replace=False, random_state=int(rng.integers(0, 2**31 - 1))
        ).copy()
        duplicate_rows["duplicate"] = True
        duplicate_rows["sequence_number"] = np.arange(
            rows + 1, rows + duplicate_count + 1, dtype=np.int64
        )
        result = pd.concat([result, duplicate_rows], ignore_index=True)

    return result.sort_values("sequence_number", kind="stable").reset_index(drop=True)


def generate_cdc(
    domain: str,
    table: str,
    rows: int,
    operations: Iterable[str] | None = None,
    late_arrival_rate: float = 0.0,
    duplicate_rate: float = 0.0,
    seed: int | None = None,
) -> pd.DataFrame:
    """Public CDC entrypoint."""

    if domain != "banking" or table != "customers":
        raise ValueError("CDC generation currently supports domain='banking', table='customers'.")

    from enterprise_synth.domains.banking import generate_pandas

    base_customers = generate_pandas(
        {
            "customers": max(rows, 25),
            "accounts": max(rows, 25),
            "cards": max(rows, 25),
            "merchants": 10,
            "transactions": max(rows, 25),
            "fraud_events": 0,
            "cdc_customer_changes": 0,
        },
        seed=seed,
    )["customers"]
    return generate_customer_cdc(
        base_customers,
        rows=rows,
        operations=tuple(operations) if operations is not None else None,
        late_arrival_rate=late_arrival_rate,
        duplicate_rate=duplicate_rate,
        seed=seed,
    )
