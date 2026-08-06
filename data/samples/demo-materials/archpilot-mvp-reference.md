# ArchPilot MVP Reference

## Purpose

ArchPilot AI is an enterprise architecture copilot for architecture knowledge, system documentation, API specifications, and operational notes.

## MVP Architecture

The MVP uses a modular monolith because it keeps feature delivery fast while preserving clear module boundaries. A modular monolith is easier to debug locally than a distributed system and avoids premature service boundaries.

## Core Capabilities

- Upload architecture documents into project-specific knowledge bases.
- Parse text, Markdown, JSON, and PDF files.
- Split documents into retrievable chunks.
- Generate embeddings when an embedding provider is configured.
- Retrieve context with vector search, keyword search, hybrid merging, reranking, and metadata filters.
- Answer questions with grounded citations.
- Persist conversations, retrieval diagnostics, evaluation runs, and feedback.

## Current Local Operations

Docker Compose starts Postgres with pgvector, the FastAPI backend, and the Next.js frontend. Alembic manages schema migrations before the API starts.

## Evaluation

The evaluation pipeline stores datasets, cases, runs, and results. It computes deterministic local metrics such as context precision, context recall, citation coverage, answer completeness, and retrieval latency.
