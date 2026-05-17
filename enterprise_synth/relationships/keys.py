"""Foreign-key registries used while creating related tables."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np


@dataclass
class KeyRegistry:
    """Store generated primary keys for deterministic child-table sampling."""

    _keys: dict[str, np.ndarray] = field(default_factory=dict)

    def register(self, table: str, keys: Iterable[int]) -> None:
        array = np.asarray(list(keys), dtype=np.int64)
        self._keys[table] = array

    def get(self, table: str) -> np.ndarray:
        try:
            return self._keys[table]
        except KeyError as exc:
            raise KeyError(f"No primary keys registered for table '{table}'.") from exc

    def sample(
        self,
        table: str,
        size: int,
        rng: np.random.Generator,
        probabilities: np.ndarray | None = None,
    ) -> np.ndarray:
        keys = self.get(table)
        if len(keys) == 0 and size:
            raise ValueError(f"Cannot sample from empty key registry for table '{table}'.")
        return rng.choice(keys, size=size, replace=True, p=probabilities)
