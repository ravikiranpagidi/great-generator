# RFC 0010: Provenance and freshness propagation

Status: Proposed
Extra: `[quality]`

## Motivation

Explore opt-in provenance and freshness annotations across generated relationship graphs for research and trust demos.

## Proposed API

`generate_domain(..., provenance=True)` or a separate `annotate_provenance(data, graph=...)` helper after approval.

## Dependencies and extra

Likely no heavy dependency at first. Visualization or graph libraries should be optional.

## Risks

This can pull the library toward a research narrative that may distract from general adoption.

## Test plan

Propagation rule tests, graph consistency tests, and docs that mark the feature as research-oriented.

## Acceptance criteria

If approved, users can demonstrate freshness and provenance propagation through generated enterprise systems.
