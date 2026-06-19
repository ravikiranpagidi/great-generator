# RFC 0006: RAG document generation

Status: Proposed
Extra: `[llm]`

## Motivation

Generate unstructured documents tied to structured rows, such as tickets, contracts, clinical notes, reviews, and support cases.

## Proposed API

`generate_documents(domain, table=..., style=..., mode=...)` with template mode by default and optional bring-your-own-key LLM mode.

## Dependencies and extra

Template mode should be core or light. Networked LLM generation must stay behind the extra and never be required.

## Risks

LLM outputs can be nondeterministic, may incur cost, and can create support complexity.

## Test plan

Template determinism tests, structured-to-document join tests, and mocked LLM provider tests.

## Acceptance criteria

Users can produce document corpora linked to generated enterprise records for RAG demos and evaluations.
