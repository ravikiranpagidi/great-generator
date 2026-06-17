# Changelog

All notable changes to this project will be documented here.

This project follows semantic versioning once public releases begin.

## Unreleased

### Added

- Added Faker-backed realistic value generation for pandas outputs.
- Added Spark-native deterministic realistic value generation for Spark outputs.
- Added `realism` mode to domain, relational, and schema generation APIs.
- Added realistic customer, patient, resident, user, merchant, product, provider, organization, company, phone, email, address, city, state, and postal-code fields where applicable.
- Added curated domain reference values for banking, ecommerce, healthcare, insurance, telecom, manufacturing, logistics, energy, hospitality, SaaS, public sector, media, and automotive-style data.
- Added tests for realistic value quality, placeholder compatibility, seed reproducibility, and relationship safety.
- Added realistic-value examples, documentation pages, and a lightweight pandas benchmark script.

### Changed

- Improved default generated datasets from placeholder-style values to more believable enterprise-style synthetic data.
- Improved README positioning, badges, API guidance, documentation links, roadmap, and package discoverability.
- Improved package metadata with Faker dependency and additional PyPI keywords.

## 0.1.0 - 2026-05-31

Initial public release candidate.

### Added

- Great Generator package identity: publish as `great-generator` and import as `great_generator`.
- Backward-compatible `enterprise_synth` import alias for pre-release users of the earlier repo name.
- Ecommerce domain pack with customers, products, orders, order items, payments, shipments, and returns.
- Banking domain pack with customers, accounts, transactions, cards, merchants, fraud events, and CDC-style customer changes.
- Healthcare domain pack with patients, providers, facilities, encounters, claims, prescriptions, and lab results.
- Telecom domain pack with customers, plans, devices, subscriptions, usage events, invoices, and support tickets.
- Logistics domain pack with shippers, warehouses, carriers, products, shipments, shipment events, and inventory movements.
- SaaS domain pack with organizations, users, plans, subscriptions, features, usage events, invoices, and support tickets.
- Insurance domain pack with customers, agents, policies, claims, premium payments, risk assessments, and reinsurance contracts.
- Automotive domain pack with customers, dealers, vehicles, sales, service appointments, warranty claims, and telematics events.
- Energy domain pack with customers, sites, meters, rate plans, usage readings, outages, and bills.
- Manufacturing domain pack with suppliers, plants, products, work orders, production runs, quality inspections, and inventory movements.
- Media domain pack with users, content titles, subscriptions, viewing events, ad campaigns, ad impressions, and game sessions.
- Public sector domain pack with residents, agencies, programs, applications, cases, payments, and service requests.
- Hospitality domain pack with customers, properties, rooms, reservations, stays, payments, and reviews.
- Shared industry-domain generator for compact domain packs with valid relationships and domain-looking values.
- Schema-driven Spark fallback for newer domain packs, preserving primary-key and foreign-key consistency.
- Deterministic generation with seeds.
- Pandas generation engine.
- Optional Spark generation engine.
- CSV, JSON, Parquet, and Delta export helpers.
- Cloud-friendly Spark path handling for local paths, DBFS, S3, ADLS, and GCS-style URIs.
- Spark export controls for writer options, partitioning, repartitioning, and coalescing.
- CDC generation for banking customer changes.
- Opt-in anomaly injection for nulls, duplicates, orphan keys, late records, out-of-order records, outliers, negative amounts, invalid statuses, and skew.
- Schema-first generation from compact schema strings, pandas DataFrames, PySpark StructTypes, and PySpark DataFrames.
- Custom relational schema generation with user-provided tables, row counts, primary keys, foreign keys, pandas/Spark output, and optional exports.
- Tests for domain generation, relationship integrity, exports, CDC, anomalies, seed reproducibility, schema generation, and optional Spark behavior.

### Notes

- Spark and Delta dependencies are optional extras.
- JSON-native nested payload generation is planned for a future release.
