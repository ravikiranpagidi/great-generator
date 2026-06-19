# RFC 0007: Fit-from-sample statistical fidelity

Status: Proposed
Extra: `[fit]`

## Motivation

Learn lightweight distribution patterns from a sample dataset and generate more rows with similar shape while staying simpler than a full SDV-style platform.

## Proposed API

`fit_from_sample(frame, seed=...)` returning a small generator object with `.sample(rows)`.

## Dependencies and extra

Use pandas and numpy first. Optional scipy-style tools must remain behind the extra if needed.

## Risks

Users may confuse this with privacy protection, and correlations can be oversold.

## Test plan

Distribution match tests, categorical frequency tests, null-rate tests, rank-correlation checks, and documentation tests for limitations.

## Acceptance criteria

Users can expand a sample dataset while preserving common patterns and explicit caveats.
