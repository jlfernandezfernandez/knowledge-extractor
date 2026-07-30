# Decisions

## One shared space, registered users

**Chosen.** All approved claims are retrieved globally by signed-in users.
Accounts provide authentication, authorship, direct interview ownership, and
review authorization. They are not a data-partitioning mechanism.

**Why.** The product demonstrates a clear social contract: people contribute to
one body of reviewed knowledge. It avoids premature access models and makes the
portfolio project easy to run and explain.

## Human approval before retrieval

**Chosen.** A contribution is extracted, reviewed, checked for overlap, and
committed only after the contributor decides.

**Why.** A language model is useful for transforming and comparing text, but it
is not an authority on what a group believes. The review graph makes
the human decision explicit and auditable through contribution history.

## PostgreSQL with pgvector

**Chosen.** PostgreSQL holds relational records, vectors, generated full-text
search data, and LangGraph checkpoints.

**Why.** One durable system makes local setup simple and allows a commit to keep
claim data and lineage together. pgvector supports semantic retrieval without
introducing another service.

## Hybrid retrieval with RRF

**Chosen.** Combine vector and full-text candidates with reciprocal rank fusion.

**Why.** Meaning-based retrieval is good at paraphrases, while lexical search
is better at exact words. RRF is a compact, explainable way to benefit from
both without training a custom ranker.

## LangGraph for the review workflow

**Chosen.** Use a small four-stage graph with PostgreSQL-backed checkpoints.

**Why.** Contribution review has real pause points and an explicit return path.
LangGraph keeps the state transitions visible in one file and lets a paused
review survive an API restart.

## React, shadcn, and browser i18n

**Chosen.** Build the interface as a React/Vite client using locally owned
shadcn components, with English and Spanish catalogs through `react-i18next`.

**Why.** React keeps feature pages and tests close together. shadcn supplies
copyable primitives rather than an opaque component runtime. Browser language
detection and typed catalogs give a small bilingual interface without a server
translation layer.

## Model and speech integrations at the edge

**Chosen.** Use the OpenAI-compatible adapter for structured model calls,
FastEmbed for local embeddings, and optional Parakeet or Whisper speech.

**Why.** Those integrations stay behind domain ports, so application code can
be tested with deterministic doubles. The local embedding path keeps the
standard stack small; speech stays optional because it is a convenience, not a
requirement for contributing.

## Deferred protocols

**MCP and A2A are deferred.** Knowli currently serves people through its
authenticated browser interface. Publishing extra protocol endpoints would add
a security and compatibility commitment before an external consumer needs one.
The application’s ports are the extension point to evaluate if that need
arrives.
