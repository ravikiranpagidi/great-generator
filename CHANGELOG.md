# Changelog

All notable changes to this project will be documented here.

This project follows semantic versioning once public releases begin.

## Unreleased

### Added

- Added a GitHub Pages documentation landing site under `docs/index.html` with install, examples, platform guidance, feature coverage, and project links.
- Added `docs/GITHUB_PAGES.md` with setup instructions for publishing the site with GitHub Actions or from the `main` branch and `/docs` folder.
- Added `.github/workflows/pages.yml` to publish the static documentation site through GitHub Pages.

### Changed

- Updated README and package project links to point documentation users to the public documentation site while keeping the GitHub Wiki linked for deeper guides.

## 0.1.4 - 2026-06-21

PyPI author presentation release.

### Changed

- Added a PyPI-friendly Author section with project links in the README.
- Updated the package documentation project link to the GitHub Wiki.

## 0.1.3 - 2026-06-21

PyPI metadata visibility release.

### Changed

- Updated package metadata so PyPI displays the author and maintainer name directly, with contact details available through project links and README.

## 0.1.2 - 2026-06-21

Schema realism quality release.

### Added

- Semantic-field based schema generation for `generate_from_schema(...)`, including abbreviation-aware column inference, realistic schema values, domain presets, custom rules, cross-field consistency, mapping schemas, and `validate_generated_data(...)`.
- Clean realistic schema data-quality rules for ages, dates, lifecycle ordering, ID safety, status-aware nulls, amount formulas, validation summaries, and semantic coverage reports.
- `explain_generation_plan(...)` for inspecting semantic inference before generating rows.
- Optional `validate=True` and `return_report=True` support for `generate_from_schema(...)`.

### Changed

- `generate_from_schema(...)` now defaults to realistic schema values. Use `realistic=False` or `realism="placeholder"` for the older placeholder-style output.
- `realism` now supports friendly aliases: `basic` and `simple` map to placeholder mode, `clean` maps to realistic mode, and the common typo `realsitic` maps to `realistic` with a warning.

## 0.1.1 - 2026-06-20

Advanced generation release.

### Added

- Labeled anomaly ground truth with `_anomaly_labels` for pandas anomaly injection.
- SCD2 history generation through `generate_domain(..., history="scd2")` and `generate_history(...)`.
- Command line interface through `great-generator`.
- Dataset recipes through `generate_from_recipe(...)` and `great-generator run`, supporting JSON, TOML, and simple YAML recipes.
- Dimensional model generation through `generate_dimensional_model(...)`, including domain-aware facts and dimensions for ecommerce and banking.
- Data Vault model generation through `generate_data_vault_model(...)`, including hubs, links, satellites, hash keys, load dates, and record sources.
- Advanced capabilities documentation and RFCs for planned optional extras such as ingestion, streaming, quality integrations, vectors, LLM document generation, fit-from-sample, differential privacy, ML training data, and provenance research.

### Changed

- README and API reference now document the advanced generation APIs.
- Optional-extra namespace now reserves `ingest`, `streaming`, `quality`, `vectors`, `llm`, `fit`, `dp`, and `all`.

## 0.1.0 - 2026-06-19

Initial public PyPI release.

### Added

- Great Generator package identity: publish as `great-generator` and import as `great_generator`.
- Backward-compatible `enterprise_synth` import alias for pre-release users of the earlier repo name.
- Faker-backed realistic value generation for pandas outputs.
- Spark-native deterministic realistic value generation for Spark outputs.
- `realism` mode for domain, relational, and schema generation APIs.
- Realistic customer, patient, resident, user, merchant, product, provider, organization, company, phone, email, address, city, state, and postal-code fields where applicable.
- Curated domain reference values for banking, ecommerce, healthcare, insurance, telecom, manufacturing, logistics, energy, hospitality, SaaS, public sector, media, and automotive-style data.
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
- Realistic-value examples, documentation pages, a GitHub Wiki, and a lightweight pandas benchmark script.
- Tests for realistic value quality, placeholder compatibility, seed reproducibility, and relationship safety.
- Tests for domain generation, relationship integrity, exports, CDC, anomalies, seed reproducibility, schema generation, and optional Spark behavior.

### Notes

- Spark and Delta dependencies are optional extras.
- JSON-native nested payload generation is planned for a future release.
