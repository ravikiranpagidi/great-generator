# RFC 0005: Vector and embedding columns

Status: Proposed
Extra: `[vectors]`

## Motivation

Generate synthetic embeddings with controllable clusters for vector database demos, similarity search tests, and RAG infrastructure benchmarks.

## Proposed API

Schema syntax for vector fields plus `generate_vectors(rows, dimensions=..., clusters=..., seed=...)`.

## Dependencies and extra

Core can use numpy. Database clients for pgvector, Milvus, or Pinecone must be optional and separate.

## Risks

Random vectors can look unrealistic, and high-dimensional output can become memory-heavy.

## Test plan

Deterministic cluster tests, dimension validation, distance distribution checks, and memory guard tests.

## Acceptance criteria

Users can generate vector columns that are useful for search and benchmark demos without calling an external model.
