# ADR 0004: Canonical serialization and hashing strategy

## Context

Contracts need stable identifiers for reproducibility, manifests, caching, and deterministic generation. Python's built-in `hash()` is process-randomized and not suitable for persisted identifiers.

## Decision

Serialize contracts into stable canonical JSON with sorted mapping keys, preserved column order, normalized unquoted identifier case, normalized type text, sorted non-order-sensitive constraints, and SHA-256 hashing.

## Alternatives considered

- Python `hash()`. Rejected because it is not stable across processes.
- Hash raw DDL text. Rejected because insignificant formatting changes would produce different identifiers.
- Hash dataclass `repr`. Rejected because it is less explicit and easier to destabilize.

## Consequences

Equivalent contracts produce the same fingerprint across SQL formatting and dictionary insertion order differences. Parser diagnostics are excluded from the hash because they are observations rather than contract semantics.

## Compatibility impact

Existing schema fingerprints remain available. `ContractSchema.fingerprint()` is additive.
