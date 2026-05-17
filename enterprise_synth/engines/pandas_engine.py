"""Pandas execution engine."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from enterprise_synth.anomalies.injector import inject_anomalies_pandas
from enterprise_synth.schemas.models import DomainSchema


def generate_domain(
    domain_module: object,
    schema: DomainSchema,
    row_counts: Mapping[str, int],
    seed: int | None,
    anomalies: Mapping[str, float] | None,
) -> dict[str, pd.DataFrame]:
    data = domain_module.generate_pandas(row_counts=row_counts, seed=seed)
    return inject_anomalies_pandas(data, schema, anomalies, seed=seed)
