# ADR 0001: Extend existing schema models for canonical contracts

## Context

Great Generator already has `ColumnSpec`, `TableSchema`, `DomainSchema`, and `ForeignKey` dataclasses used by domain packs, validation, generation, relationship handling, and advisor planning. M1A needs contract-level metadata without destabilizing those public models.

## Decision

Extend the existing dataclasses and add `ContractSchema` in the same schema model module. Add optional metadata fields for original types, composite keys, unique constraints, check constraints, namespaces, tags, and extension metadata. Preserve the original positional constructors where practical.

## Alternatives considered

- Create a separate contract object hierarchy. Rejected because it would duplicate schemas and force adapters across generation, planning, and validation.
- Introduce Pydantic as the base model layer. Rejected for M1A because dataclasses meet the current requirements and avoid a new validation dependency.

## Consequences

The contract model integrates naturally with existing planning and generation. The tradeoff is that `TableSchema` is now more capable and slightly more verbose when serialized.

## Compatibility impact

Existing constructors such as `ColumnSpec("id", "int")`, `TableSchema(...)`, and `ForeignKey("customer_id", "customers", "customer_id")` remain valid.
