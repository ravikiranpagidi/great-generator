# Open-source strategy

## Name ideas

- **Great Generator** - direct, memorable, accurately scoped
- **Relata** - evokes relationships and data lineage
- **DataForge** - strong builder energy, broader than the current focus
- **DomainGen** - practical and literal
- **SynthLake** - strong lakehouse association, narrower than the whole product

## Recommendation

Use **Great Generator** as the product name, publish as `great-generator`, and import as `great_generator`.
It says what the library does without making users decode a metaphor.

## GitHub strategy

- Keep the repository clean, example-heavy, and test-rich.
- Open with a screenshot-ready README quickstart.
- Use labels such as `good first issue`, `documentation`, `enhancement`, `bug`, `domain-pack`, `realistic-values`, `spark`, `pandas`, and `testing`.
- Recommended GitHub topics: `synthetic-data`, `data-engineering`, `pandas`, `spark`, `pyspark`, `databricks`, `lakehouse`, `delta-lake`, `faker`, `test-data`, `data-generation`, `mock-data`, `analytics-engineering`, `data-quality`, `cdc`, `benchmarking`, `python`, and `open-source`.
- Keep discussions focused on domain packs, benchmarks, realistic values, exports, and reproducibility.
- Add issue templates for bug reports, domain-pack proposals, realistic-value improvements, and feature requests.

## Starter issues

- Add realistic values for telecom plans and device models.
- Add ecommerce dashboard demo notebook.
- Add Spark benchmark script for cluster runs.
- Improve API reference docs with more examples.
- Add Great Expectations integration example.
- Add Microsoft Fabric demo using generated Parquet data.
- Add more realistic healthcare provider and facility reference values.
- Add tests for realistic optional-null distribution.

## PyPI strategy

1. Reserve `great-generator` early.
2. Publish an alpha release once the public API, README, and examples are coherent.
3. Tag releases semantically and maintain a concise changelog.
4. Ship wheels and source distributions through trusted publishing.
5. Keep optional extras (`spark`, `delta`, `dev`) honest and documented.

## Adoption strategy

- Lead with one-line examples and generated table screenshots in notebooks.
- Publish short recipes: lakehouse demo, CDC test harness, dbt seed data, Spark benchmark.
- Add domain packs where communities already teach with examples: healthcare, telecom, SaaS, logistics.
- Encourage talks and tutorials by keeping outputs visually attractive and realistic enough to tell a story.
- Treat every new domain pack as both a feature and a teaching artifact.
