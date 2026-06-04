"""Deterministic randomness helpers."""

from __future__ import annotations

import hashlib

import numpy as np


def derive_seed(seed: int | None, namespace: str) -> int | None:
    """Derive a stable child seed from a root seed and namespace."""

    if seed is None:
        return None
    digest = hashlib.sha256(f"{seed}:{namespace}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % (2**32 - 1)


def get_rng(seed: int | None, namespace: str = "root") -> np.random.Generator:
    return np.random.default_rng(derive_seed(seed, namespace))
