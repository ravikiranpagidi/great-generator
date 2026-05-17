"""Calendar-aware sampling helpers."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


def weighted_calendar_dates(
    rng: np.random.Generator,
    rows: int,
    start: str = "2024-01-01",
    end: str = "2025-12-31",
    weekend_multiplier: float = 1.3,
    holiday_multiplier: float = 1.8,
    payroll_multiplier: float = 1.0,
) -> pd.DatetimeIndex:
    """Sample dates with realistic weekend, holiday, and payroll boosts."""

    calendar = pd.date_range(start=start, end=end, freq="D")
    weights = np.ones(len(calendar), dtype=float)

    weekend_mask = calendar.weekday >= 5
    weights[weekend_mask] *= weekend_multiplier

    holiday_mask = (
        ((calendar.month == 11) & (calendar.day >= 20))
        | ((calendar.month == 12) & (calendar.day <= 31))
        | ((calendar.month == 7) & (calendar.day <= 7))
    )
    weights[holiday_mask] *= holiday_multiplier

    if payroll_multiplier != 1.0:
        payroll_mask = calendar.day.isin([1, 15, 28])
        weights[payroll_mask] *= payroll_multiplier

    probabilities = weights / weights.sum()
    chosen = rng.choice(calendar.to_numpy(), size=rows, replace=True, p=probabilities)
    return pd.DatetimeIndex(chosen)


def random_timestamps_on_dates(
    rng: np.random.Generator,
    dates: pd.DatetimeIndex,
    business_hours_bias: float = 0.7,
) -> pd.Series:
    """Attach times of day with more activity during business hours."""

    rows = len(dates)
    business_mask = rng.random(rows) < business_hours_bias
    hours = np.where(business_mask, rng.integers(8, 21, rows), rng.integers(0, 24, rows))
    minutes = rng.integers(0, 60, rows)
    seconds = rng.integers(0, 60, rows)
    offsets = (
        pd.to_timedelta(hours, unit="h")
        + pd.to_timedelta(minutes, unit="m")
        + pd.to_timedelta(seconds, unit="s")
    )
    return pd.Series(dates + offsets)


def as_date(value: pd.Timestamp | date) -> date:
    return value.date() if isinstance(value, pd.Timestamp) else value
