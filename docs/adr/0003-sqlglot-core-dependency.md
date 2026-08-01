# ADR 0003: Add SQLGlot as a core dependency

## Context

The product direction is contract-first generation. Full SQL DDL ingestion is now a core workflow, not a niche optional extension.

## Decision

Add `sqlglot>=25.0.0` to core dependencies.

## Package-size impact

The installed wheel checked during implementation was under 1 MB. It is pure Python and does not add native libraries.

## Supported Python versions

The installed SQLGlot metadata reports `Requires-Python: >=3.9`, matching Great Generator's minimum Python version.

## Maintenance implications

SQLGlot is an external parser dependency, so Great Generator must keep focused parser tests for the supported subset and avoid claiming untested dialect coverage.

## Could it remain optional?

It could be optional behind a future extra, but that would make the advertised contract-first DDL path fail after a normal install. Core dependency is the better first-release user experience for this milestone.

## Alternatives considered

- Optional `ddl` extra. Rejected because DDL ingestion is now central positioning.
- Vendor or write a parser. Rejected due maintenance burden and lower correctness.

## Compatibility impact

Normal installation adds one pure-Python dependency. Spark and Delta remain optional.
