# Open-source strategy

## Name ideas

- **Enterprise Synth** ? direct, memorable, accurately scoped
- **Relata** ? evokes relationships and data lineage
- **DataForge** ? strong builder energy, broader than the current focus
- **DomainGen** ? practical and literal
- **SynthLake** ? strong lakehouse association, narrower than the whole product

## Recommendation

Use **Enterprise Synth** as the product name, publish as `enterprise-synth`, and import as `enterprise_synth`.
It says what the library does without making users decode a metaphor.

## GitHub strategy

- Keep the repository clean, example-heavy, and test-rich.
- Open with a screenshot-ready README quickstart.
- Use labels such as `domain-pack`, `good first issue`, `spark`, `exports`, and `cdc`.
- Keep discussions focused on domain packs, benchmarks, and reproducibility.
- Add issue templates for bug reports, domain-pack proposals, and feature requests.

## PyPI strategy

1. Reserve `enterprise-synth` early.
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
