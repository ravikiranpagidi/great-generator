"""Pandas execution engine."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from great_generator.anomalies.injector import inject_anomalies_pandas
from great_generator.schemas.generation import generate_domain_schema_pandas
from great_generator.schemas.models import DomainSchema


def generate_domain(
    domain_module: object,
    schema: DomainSchema,
    row_counts: Mapping[str, int],
    seed: int | None,
    anomalies: Mapping[str, float] | None,
) -> dict[str, pd.DataFrame]:
    if domain_module is None:
        data = generate_domain_schema_pandas(schema, rows=row_counts, seed=seed)
    else:
        data = domain_module.generate_pandas(row_counts=row_counts, seed=seed)
    return inject_anomalies_pandas(data, schema, anomalies, seed=seed)
