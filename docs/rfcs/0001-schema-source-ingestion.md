# RFC 0001: Schema-source ingestion

Status: Proposed
Extra: `[ingest]`

## Motivation

Read schemas users already have, including JSON Schema, Avro, Protobuf, dbt YAML, SQLAlchemy reflection, and lakehouse catalog schemas, then generate conforming data.

## Proposed API

`generate_from_source(source, source_type=..., rows=..., engine=...)` and focused helpers such as `generate_from_json_schema(...)`.

## Dependencies and extra

Format-specific libraries may be needed. Keep each heavy parser behind a sub-extra when required.

## Risks

Schema dialects differ, nested types can be ambiguous, and live database reflection can expose credentials if handled poorly.

## Test plan

Golden schema fixtures for every supported format, determinism tests, nested type tests, and clear error tests for missing extras.

## Acceptance criteria

Users can point the library at an existing schema and receive type-correct pandas or Spark output with clear limitations.
