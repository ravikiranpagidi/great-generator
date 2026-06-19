# RFC 0002: Streaming generation

Status: Proposed
Extra: `[streaming]`

## Motivation

Emit reproducible event streams for CDC pipelines, Spark Structured Streaming, Kafka demos, Kinesis, Event Hubs, and iterator-based local tests.

## Proposed API

`stream_domain(domain, events_per_sec=..., sink=..., seed=...)` plus a no-extra Python iterator sink.

## Dependencies and extra

Kafka, Kinesis, and Event Hubs clients should remain optional. Iterator mode should require no new dependency.

## Risks

Wall-clock timing is not deterministic, sinks have different delivery guarantees, and streaming failures are harder to reproduce.

## Test plan

Seed-reproducible iterator tests, sink contract tests with fakes, rate-shaping tests, and CDC ordering tests.

## Acceptance criteria

A user can run a local iterator stream and optionally route equivalent events into supported streaming platforms.
