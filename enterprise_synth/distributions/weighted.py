"""Reusable weighted-distribution helpers."""

from __future__ import annotations

import numpy as np


def normalize(weights: np.ndarray) -> np.ndarray:
    total = float(weights.sum())
    if total <= 0:
        raise ValueError("Weights must sum to a positive value.")
    return weights / total


def pareto_like_weights(size: int, alpha: float = 1.35) -> np.ndarray:
    """Create descending weights that mimic 80/20-ish behavior."""

    ranks = np.arange(1, size + 1, dtype=float)
    return normalize(1 / np.power(ranks, alpha))


def weighted_choice(
    rng: np.random.Generator,
    values: np.ndarray,
    size: int,
    weights: np.ndarray,
) -> np.ndarray:
    return rng.choice(values, size=size, replace=True, p=normalize(weights))
