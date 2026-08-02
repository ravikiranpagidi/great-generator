# Benchmark Contributions

Benchmark contributions are welcome when they are transparent, reproducible, and environment-specific.

## Good benchmark contributions

- Add a new benchmark case with clear row counts.
- Add JSON output from the benchmark harness.
- Document the machine, runtime, and dependency versions.
- Separate generation time from export/write time.
- Avoid broad claims that one run proves universal performance.

## Pull request checklist

- Explain what workload was measured.
- Include the command used to run the benchmark.
- Include the package version or commit.
- Include runtime details.
- State whether the run was local Pandas, local Spark, or cluster Spark.
- State whether data was written to disk/cloud/database.
- Include caveats for memory, partitioning, and storage.

## Example command

```bash
python benchmarks/benchmark_pandas_generation.py \
  --case ecommerce:small \
  --case banking:small \
  --repeat 3 \
  --json benchmark-results.json
```
