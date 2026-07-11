# Great Generator 0.1.6 Release Notes

Release date: 2026-07-11

## Summary

Great Generator 0.1.6 adds an optional AI advisor planning layer. The advisor layer helps at design time with schema understanding, column semantic tagging, and realism review. It does not generate row data.

Generation remains deterministic. The default remains `advisor="none"`, which makes no model calls, reads no API keys, and sends nothing over the network.

## Main features

| Area | What changed |
|---|---|
| Advisor entry points | Added `infer_generation_plan(...)`, `tag_schema(...)`, and `review_realism(...)`. |
| Planning artifacts | Added `GenerationPlan`, `ColumnTags`, and `RealismReport` as inspectable JSON artifacts. |
| Deterministic generation | Added optional `plan=` support to `generate_from_schema(...)`. Existing behavior is unchanged when no plan is passed. |
| Advisor implementations | Added NoOp default, Anthropic support, Ollama support, and clear OpenAI and llama.cpp stubs. |
| Offline path | Ollama and NoOp support local and offline workflows. |
| Caching | Advisor calls are cached under `.gg_cache/` by advisor, model, prompt version, and canonical input hash. |
| Audit metadata | Added manifest helper metadata for advisor contribution, plan fingerprint, cache hit state, and human review state. |
| Docs | Added advisor docs, plan docs, README guidance, API reference updates, and Wiki pages. |

## Example

```python
from great_generator import generate_from_schema, infer_generation_plan

schema = "customer_id int, customer_name string, email string"

plan = infer_generation_plan(schema, advisor="none")
df = generate_from_schema(schema, rows=1000, plan=plan)
```

## Optional advisor installs

```bash
pip install "great-generator[ai]"
pip install "great-generator[anthropic]"
pip install "great-generator[ollama]"
```

## Notes

- Advisors are opt-in.
- `advisor="none"` is the default and never touches the network.
- LLMs do not create row data in this release.
- Plans and tags are JSON artifacts that can be reviewed and committed.
- Same schema, plan, seed, and generation arguments produce the same data.
