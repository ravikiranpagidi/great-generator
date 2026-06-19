# RFC 0004: Medallion plus catalog-native output

Status: Proposed
Extra: `[spark, delta]`

## Motivation

Generate bronze, silver, and gold layers from the same synthetic domain and optionally register managed tables with comments and tags.

## Proposed API

`generate_medallion_domain(domain, catalog=..., schema=..., register=True, ...)`.

## Dependencies and extra

No new core dependencies. Requires Spark and Delta support, catalog registration should stay adapter-based.

## Risks

Catalog permissions vary by platform, and registration behavior differs across Unity Catalog, Hive metastore, and Fabric-like catalogs.

## Test plan

Local Spark Delta tests where available, SQL generation tests, and mocked catalog adapter tests.

## Acceptance criteria

Users can demo a full lakehouse pipeline with raw, cleaned, and curated layers from one command.
