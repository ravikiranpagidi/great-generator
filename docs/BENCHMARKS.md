# Benchmarks

Great Generator includes a lightweight pandas benchmark harness:

```bash
python benchmarks/benchmark_pandas_generation.py
```

The script reports generation time for selected domains and scale profiles.

Benchmark results depend on:

- Python version
- pandas and numpy versions
- machine memory and CPU
- selected domain
- selected scale
- whether exports are included

Spark and Delta benchmarks should be measured in the target cluster/runtime because throughput depends heavily on executor count, partitions, storage, and file format settings.
