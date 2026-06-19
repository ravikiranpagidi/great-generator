"""Command line interface for Great Generator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from great_generator.api import (
    generate_domain,
    generate_from_recipe,
    get_domain_schema,
    list_domains,
)


def main(argv: list[str] | None = None) -> int:
    """Run the Great Generator command line interface."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        parser.exit(1, f"great-generator: error: {exc}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="great-generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-domains", help="List available domain packs.")
    list_parser.set_defaults(func=_list_domains)

    describe_parser = subparsers.add_parser("describe", help="Describe a domain schema.")
    describe_parser.add_argument("domain")
    describe_parser.add_argument(
        "--json", action="store_true", help="Print schema metadata as JSON."
    )
    describe_parser.set_defaults(func=_describe)

    gen_parser = subparsers.add_parser("gen", help="Generate a domain dataset.")
    gen_parser.add_argument("domain")
    gen_parser.add_argument("--engine", default="pandas", choices=["pandas", "spark"])
    gen_parser.add_argument("--scale", default="tiny")
    gen_parser.add_argument("--realism", default="realistic")
    gen_parser.add_argument("--seed", type=int)
    gen_parser.add_argument("--out", required=True)
    gen_parser.add_argument("--format", default="csv", choices=["csv", "json", "parquet", "delta"])
    gen_parser.set_defaults(func=_generate)

    run_parser = subparsers.add_parser("run", help="Run a JSON or TOML dataset recipe.")
    run_parser.add_argument("recipe")
    run_parser.set_defaults(func=_run_recipe)

    return parser


def _list_domains(_args: argparse.Namespace) -> int:
    for domain in list_domains():
        print(domain)
    return 0


def _describe(args: argparse.Namespace) -> int:
    schema = get_domain_schema(args.domain)
    if args.json:
        print(json.dumps(schema.as_dict(), indent=2, default=str))
        return 0
    print(f"{schema.name}: {schema.description}")
    for table_name, table in schema.tables.items():
        print(f"- {table_name}: {len(table.columns)} columns")
    return 0


def _generate(args: argparse.Namespace) -> int:
    generate_domain(
        args.domain,
        engine=args.engine,
        scale=args.scale,
        realism=args.realism,
        seed=args.seed,
        output_path=Path(args.out),
        output_format=args.format,
    )
    print(f"generated {args.domain} at {args.out}")
    return 0


def _run_recipe(args: argparse.Namespace) -> int:
    data = generate_from_recipe(args.recipe)
    print(f"generated {len(data)} tables from {args.recipe}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
