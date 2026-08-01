# ADR 0002: Use SQLGlot for SQL DDL parsing

## Context

M1A requires full `CREATE TABLE` ingestion for a documented ANSI, Spark, and Databricks subset. The implementation must not rely on regex-only parsing.

## Decision

Use SQLGlot as the SQL parser for M1A. Great Generator reads the SQLGlot syntax tree, then maps supported expressions into the canonical contract model.

## Alternatives considered

- Regex-only parser. Rejected because it is brittle and explicitly outside the M1A requirements.
- `sqlparse`. Rejected because it tokenizes and formats SQL but provides less semantic AST support for constraints and DDL.
- Database-specific parsers. Rejected because M1A needs a small multi-dialect surface, especially Spark and Databricks.

## Consequences

SQLGlot gives the project a maintained AST layer and avoids building a SQL parser. Great Generator still owns the supported subset, diagnostics, and canonical model mapping.

## Compatibility impact

No existing user-facing API is removed. Full DDL support is additive through `parse_ddl(...)` and contract input support in `generate_from_schema(...)`.
