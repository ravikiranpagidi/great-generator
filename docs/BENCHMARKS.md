# Benchmark Methodology

Great Generator includes a lightweight local Pandas benchmark harness.

```bash
python benchmarks/benchmark_pandas_generation.py
```

Run selected cases:

```bash
python benchmarks/benchmark_pandas_generation.py --case ecommerce:small --case banking:small --repeat 3
```

Write JSON results:

```bash
python benchmarks/benchmark_pandas_generation.py --case ecommerce:small --repeat 3 --json benchmark-results.json
```

## What the benchmark measures

The harness measures in-memory Pandas domain generation time for selected domain/scale pairs. It reports:

- domain
- scale
- run number
- total generated rows across tables
- elapsed seconds
- rows per second
- Python, platform, Great Generator, Pandas, and NumPy versions

## What it does not measure

The local harness does not measure:

- Spark cluster throughput
- Delta Lake transaction overhead
- cloud object storage write throughput
- database connector speed
- notebook startup time
- dashboard query latency
- memory pressure at all possible row counts

## Responsible scale wording

Great Generator is designed to support small to large datasets. It can be used to generate datasets ranging from one row to very large row counts depending on the user's environment, memory, compute, schema complexity, and engine.

For very large datasets, chunking or Spark-native generation is recommended.

Do not present a row-count setting as a universal performance guarantee unless you have tested that workload in the target environment.

## Suggested benchmark report format

When sharing results, include:

- machine or cluster type
- Python version
- package version
- Pandas, NumPy, Spark, and Delta versions where relevant
- OS/runtime
- dataset/domain
- row counts per table
- whether exports were included
- output format and storage system
- cold vs warm run behavior

## Spark and cloud benchmarks

Spark and cloud benchmarks should be run in the target runtime because performance depends on executor count, partitioning, file format, storage, catalog behavior, and connector settings.

Good Spark benchmark notes include:

- Spark runtime and version
- number of executors and cores
- memory per executor
- `num_partitions`
- output path type: local, DBFS, ADLS, S3, GCS, or lakehouse path
- output format: Parquet or Delta
- partition columns
- compression settings
- table/catalog registration behavior
