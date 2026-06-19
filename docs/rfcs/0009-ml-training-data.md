# RFC 0009: ML training data with drift

Status: Proposed
Extra: `[fit]`

## Motivation

Generate point-in-time-correct features, labels, class balance, label noise, and concept drift for ML education and research demos.

## Proposed API

`generate_ml_dataset(domain, target=..., drift=..., label_noise=..., seed=...)`.

## Dependencies and extra

Keep ML framework dependencies out of core. Pandas output first, optional sklearn helpers only if needed.

## Risks

Feature leakage is easy to introduce, and labels can look arbitrary without domain logic.

## Test plan

Leakage tests, class-balance tests, drift-period tests, and reproducibility tests.

## Acceptance criteria

Users can generate ML-ready data with realistic time behavior and documented target semantics.
