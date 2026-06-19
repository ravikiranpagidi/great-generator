# RFC 0008: Differential privacy on the fit path

Status: Proposed
Extra: `[dp]`

## Motivation

Add calibrated noise to fit-from-sample statistics so one narrow path can make a clear privacy claim.

## Proposed API

`fit_from_sample(..., privacy={"epsilon": ...})` or a dedicated `fit_private(...)` helper.

## Dependencies and extra

Requires a carefully selected DP library or a small audited internal mechanism. This cannot enter core casually.

## Risks

Privacy claims are high-stakes, easy to misstate, and need precise threat-model language.

## Test plan

Mathematical unit tests for mechanisms, documentation review, regression tests for privacy parameters, and examples with warnings.

## Acceptance criteria

The README can honestly describe one privacy-scoped fit mode with exact guarantees and limitations.
