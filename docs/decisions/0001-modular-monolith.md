# Decision: Use a Modular Monolith for the MVP

Date: 2026‑03‑15

## Status
Accepted

## Context

Building a scalable AI copilot system often requires multiple microservices: ingestion pipelines, retrieval engines, API gateways, LLM proxies and more.  However, splitting into microservices too early can slow down development, introduce operational overhead and obscure the logical structure of the codebase.

Our immediate goal is to create a portfolio project that demonstrates architectural clarity and can be delivered by a single developer.  It should be easy to understand, run locally, and evolve.

## Decision

We will implement the MVP as a **modular monolith**:

- All backend modules will live in a single FastAPI application.
- Clear, stable boundaries between concerns (ingestion, retrieval, copilot orchestration, LLM gateway, evaluation) will be enforced via directories and interfaces.
- The database will be shared across modules.

This structure allows us to achieve simplicity of deployment while still communicating an architecture that could be broken into services later.

## Consequences

### Positive

* Fast local development and simpler debugging
* Unified source tree makes navigating the code easier for reviewers
* No network latency or service discovery to worry about
* Future migration to microservices is straightforward because each module is already separated

### Negative

* Shared runtime means module failures could affect the entire app
* Scaling individual modules independently is not possible without refactoring

We accept these trade‑offs for the MVP and will revisit them if/when the project grows in complexity.