"""Pandas execution engine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import pandas as pd

from great_generator.anomalies.injector import inject_anomalies_pandas
from great_generator.core.realism import apply_realism_pandas
from great_generator.schemas.generation import generate_domain_schema_pandas
from great_generator.schemas.models import DomainSchema


class DomainModule(Protocol):
    def generate_pandas(
        self, row_counts: Mapping[str, int], seed: int | None
    ) -> dict[str, pd.DataFrame]: ...


def generate_domain(
    domain_module: DomainModule | None,
    schema: DomainSchema,
    row_counts: Mapping[str, int],
    seed: int | None,
    anomalies: Mapping[str, float] | None,
    realism: str = "realistic",
) -> dict[str, pd.DataFrame]:
    if domain_module is None:
        data = generate_domain_schema_pandas(schema, rows=row_counts, seed=seed)
    else:
        data = domain_module.generate_pandas(row_counts=row_counts, seed=seed)
    data = apply_realism_pandas(data, schema, seed=seed, realism=realism)
    return inject_anomalies_pandas(data, schema, anomalies, seed=seed)
