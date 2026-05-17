"""Dependency-graph utilities for domain generation."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping


def topological_sort(dependencies: Mapping[str, set[str]]) -> list[str]:
    """Return a deterministic topological ordering or raise on cycles."""

    remaining = {node: set(parents) for node, parents in dependencies.items()}
    ready = deque(sorted(node for node, parents in remaining.items() if not parents))
    order: list[str] = []

    while ready:
        node = ready.popleft()
        order.append(node)
        for candidate in sorted(remaining):
            if node in remaining[candidate]:
                remaining[candidate].remove(node)
                if not remaining[candidate] and candidate not in order and candidate not in ready:
                    ready.append(candidate)

    if len(order) != len(remaining):
        unresolved = sorted(node for node, parents in remaining.items() if parents)
        raise ValueError(f"Dependency graph contains a cycle involving: {unresolved}")
    return order
