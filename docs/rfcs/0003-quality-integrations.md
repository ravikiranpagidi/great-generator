# RFC 0003: Data-quality integrations and pytest plugin

Status: Proposed
Extra: `[quality]`

## Motivation

Generate not only data, but also validation suites and pytest fixtures so teams can adopt synthetic enterprise data inside normal test workflows.

## Proposed API

`generate_quality_suite(data, framework=...)` and pytest fixtures exposed by a `pytest11` entry point.

## Dependencies and extra

Great Expectations, Soda, and Pandera should be optional dependencies under this extra.

## Risks

Generated rules can be too strict for anomaly-rich datasets, and framework APIs change often.

## Test plan

Snapshot tests for generated suites, pytest plugin smoke tests, and framework-specific optional test groups.

## Acceptance criteria

Users can generate data plus validation rules, then run those checks in their preferred quality framework.
