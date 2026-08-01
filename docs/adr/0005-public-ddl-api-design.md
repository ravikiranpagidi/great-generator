# ADR 0005: Add function-first DDL API

## Context

Great Generator's public API is function-first. M1A should not replace that with an object-oriented facade.

## Decision

Add `parse_ddl(...)` as an additive top-level function. It returns a `ContractSchema`, which can be passed to existing APIs such as `generate_from_schema(...)`, `infer_generation_plan(...)`, `explain_generation_plan(...)`, and `validate_generated_data(...)`.

## Alternatives considered

- Add a `GreatGenerator` class facade now. Deferred because it is not required for M1A.
- Add `engine="ddl"`. Rejected because `engine` means execution engine and must remain `pandas`, `spark`, or `auto` where applicable.
- Add many parser-specific public functions. Rejected to keep the surface small.

## Consequences

Users get a simple contract-first path without changing existing workflows. Future JSON Schema or dbt ingestion can reuse the parser abstraction without adding placeholder APIs today.

## Compatibility impact

Existing APIs remain compatible. Full SQL DDL and `ContractSchema` support are additive.
