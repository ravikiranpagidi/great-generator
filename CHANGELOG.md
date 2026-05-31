# Changelog

All notable changes to this project will be documented here.

This project follows semantic versioning once public releases begin.

## 0.1.0 - 2026-05-31

Initial public release candidate.

### Added

- Ecommerce domain pack with customers, products, orders, order items, payments, shipments, and returns.
- Banking domain pack with customers, accounts, transactions, cards, merchants, fraud events, and CDC-style customer changes.
- Deterministic generation with seeds.
- Pandas generation engine.
- Optional Spark generation engine.
- CSV, JSON, Parquet, and Delta export helpers.
- Cloud-friendly Spark path handling for local paths, DBFS, S3, ADLS, and GCS-style URIs.
- Spark export controls for writer options, partitioning, repartitioning, and coalescing.
- CDC generation for banking customer changes.
- Opt-in anomaly injection for nulls, duplicates, orphan keys, late records, out-of-order records, outliers, negative amounts, invalid statuses, and skew.
- Schema-first generation from compact schema strings, pandas DataFrames, PySpark StructTypes, and PySpark DataFrames.
- Tests for domain generation, relationship integrity, exports, CDC, anomalies, seed reproducibility, schema generation, and optional Spark behavior.

### Notes

- Spark and Delta dependencies are optional extras.
- JSON-native nested payload generation is planned for a future release.
