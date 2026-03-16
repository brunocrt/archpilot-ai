# Architecture of ArchPilot AI

This document provides a high‑level overview of the system architecture for ArchPilot AI.  The design follows a modular monolith pattern to allow rapid development while keeping clear boundaries between functional concerns. Each module can later be extracted into its own service if necessary.

## Components

### Frontend (apps/web)

The web UI is a simple Next.js application that allows users to:

* Upload documents to the knowledge base
* Ask questions and receive answers with citations
* View conversation history and provide feedback

It communicates with the backend via RESTful APIs exposed by the FastAPI application.

### API Gateway / BFF (apps/api/app)

This component provides a thin layer that defines HTTP endpoints. It performs request validation, handles authentication (future work), and invokes underlying services.  It is implemented using FastAPI.

### Ingestion Service

The ingestion service is responsible for processing uploaded files.  It performs:

1. **Parsing:** converting various formats (txt, markdown, PDF, etc.) into plain text.
2. **Chunking:** splitting large documents into smaller chunks suitable for embedding and retrieval.
3. **Embedding:** generating vector representations for each chunk using a language model (e.g., OpenAI embeddings).
4. **Persistence:** storing documents and chunks along with metadata in Postgres and pgvector.

### Retrieval Service

This module handles hybrid search over the knowledge base. Given a query, it embeds the query, performs vector similarity search in pgvector, applies optional metadata filters, and returns the most relevant chunks.

### Copilot Service

The copilot orchestrator glues together retrieval and the language model. It constructs prompts that include retrieved context, calls the language model via the LLM gateway, and post‑processes the response to include citations.

### LLM Gateway

An abstraction over one or more language model providers. It encapsulates API keys, error handling, and provider selection logic. This makes it easy to swap providers or route requests based on model capabilities.

### Evaluation & Feedback

As part of building a trustworthy system, we log retrieval metadata, track user feedback, and provide a hook for automated evaluation (e.g. grounding detection or relevancy scoring).  These components are minimal in the MVP but provide a foundation for future improvements.

### Database

ArchPilot AI uses Postgres for structured data and the pgvector extension for vector embeddings.  All metadata, document contents, chunks, conversations and logs are stored here.  See `app/domain/models.py` for schema definitions.

## Data Flow

1. **Upload:** A user uploads a document via the web UI.  The API accepts the upload, stores the raw file, and enqueues an ingestion job (synchronous in the MVP).
2. **Ingestion:** The ingestion service parses the file, chunks the text, generates embeddings, and persists the document and its chunks in the database.
3. **Query:** When the user asks a question, the copilot service calls the retrieval service to fetch relevant chunks, constructs a prompt using the `answer_with_citations` template, and calls the LLM gateway.
4. **Response:** The LLM responds with a grounded answer. The copilot service packages the answer with citations and saves the conversation.  The web UI displays the answer and retrieved sources to the user.

## Extensibility

This architecture is intentionally modular.  Each service could be replaced or extended independently:

- Swap the embedding model or vector database without changing other parts
- Add new data sources or file types to the ingestion service
- Introduce hybrid retrieval with keyword search and reranking
- Plug in different LLM providers or route by task
- Add role‑based access control and policy enforcement in a central audit module

For details on architectural decisions, see the decision records in `docs/decisions/`.