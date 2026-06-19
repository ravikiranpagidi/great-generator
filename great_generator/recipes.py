"""Dataset recipe loading and execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_recipe(path: str | Path) -> dict[str, Any]:
    """Load a JSON, TOML, or simple YAML dataset recipe."""

    recipe_path = Path(path)
    suffix = recipe_path.suffix.lower()
    text = recipe_path.read_text(encoding="utf-8")
    if suffix == ".json":
        loaded = json.loads(text)
    elif suffix == ".toml":
        try:
            import tomllib
        except ModuleNotFoundError as exc:  # pragma: no cover, Python 3.10 and lower
            raise ImportError("TOML recipes require Python 3.11 or newer.") from exc
        loaded = tomllib.loads(text)
    elif suffix in {".yaml", ".yml"}:
        loaded = _parse_simple_yaml(text)
    else:
        raise ValueError("Recipe files must use .json, .toml, .yaml, or .yml.")
    if not isinstance(loaded, dict):
        raise ValueError("Recipe root must be an object.")
    return loaded


def generate_from_recipe(path: str | Path) -> dict[str, Any]:
    """Generate a dataset from a declarative recipe file."""

    recipe = load_recipe(path)
    kind = str(recipe.get("kind", "domain")).lower()
    output = recipe.get("output", {})
    if output is None:
        output = {}
    if not isinstance(output, dict):
        raise ValueError("Recipe 'output' must be an object when provided.")

    if kind == "domain":
        from great_generator.api import generate_domain

        domain = _required_string(recipe, "domain")
        return generate_domain(
            domain,
            engine=str(recipe.get("engine", "pandas")),
            scale=str(recipe.get("scale", "tiny")),
            rows=recipe.get("rows"),
            seed=recipe.get("seed"),
            realism=str(recipe.get("realism", "realistic")),
            anomalies=recipe.get("anomalies"),
            output_path=output.get("path"),
            output_format=output.get("format"),
        )

    if kind == "relational":
        from great_generator.api import generate_relational

        tables = recipe.get("tables")
        if not isinstance(tables, dict):
            raise ValueError("Relational recipes require a 'tables' object.")
        return generate_relational(
            tables=tables,
            relationships=recipe.get("relationships"),
            rows=recipe.get("rows"),
            engine=str(recipe.get("engine", "pandas")),
            seed=recipe.get("seed"),
            realism=str(recipe.get("realism", "realistic")),
            anomalies=recipe.get("anomalies"),
            output_path=output.get("path"),
            output_format=output.get("format"),
        )

    raise ValueError("Recipe kind must be 'domain' or 'relational'.")


def _required_string(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"Recipe must include '{key}'.")
    return str(value)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse a small YAML mapping without adding a runtime dependency.

    This intentionally supports the recipe shape Great Generator documents:
    nested key/value mappings with scalar values. For complex YAML features,
    users should convert the recipe to JSON or TOML.
    """

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(0, root)]
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        without_comment = raw_line.split("#", 1)[0].rstrip()
        if not without_comment.strip():
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        content = without_comment.strip()
        key, separator, raw_value = content.partition(":")
        if not separator or not key.strip():
            raise ValueError(f"Invalid YAML recipe line {line_number}: expected key: value.")

        while stack and indent < stack[-1][0]:
            stack.pop()
        if not stack:
            raise ValueError(f"Invalid YAML recipe indentation at line {line_number}.")
        if indent > stack[-1][0]:
            raise ValueError(f"Invalid YAML recipe indentation at line {line_number}.")

        parent = stack[-1][1]
        key = key.strip()
        value = raw_value.strip()
        if not value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent + 2, child))
        else:
            parent[key] = _parse_yaml_scalar(value)
    return root


def _parse_yaml_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"null", "none", "~"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value
