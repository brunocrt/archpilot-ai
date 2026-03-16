# ArchPilot AI

ArchPilot AI is an enterprise‑grade AI copilot platform for querying architecture knowledge, system documentation, API specs and operational documents using grounded retrieval and policy‑aware AI workflows.

## Why this project

Many AI demos stop at simple chat over documents. ArchPilot AI is designed to show how a real enterprise AI copilot can be built with:

- Document ingestion
- Vector retrieval
- Grounded LLM responses
- Source citations
- Conversation history
- Feedback logging
- Model provider abstraction

This repository provides an opinionated but extensible starting point for building such a system. It is organised as a modular monolith so you can develop quickly while maintaining clean separation of concerns.  Later on you could split services out behind separate processes without rewriting the core logic.

## Project structure

```
archpilot-ai/
├── apps/
│   ├── api/                    # Python backend (FastAPI)
│   │   └── app/
│   │       ├── main.py        # Entrypoint for FastAPI
│   │       ├── config.py      # Environment & settings management
│   │       ├── db.py          # SQLAlchemy database session
│   │       ├── dependencies.py# Shared dependencies (e.g. DB session)
│   │       ├── logging_config.py  # Logging configuration
│   │       ├── api/           # HTTP route handlers
│   │       │   ├── health.py
│   │       │   ├── documents.py
│   │       │   ├── chat.py
│   │       │   └── feedback.py
│   │       ├── domain/        # SQLAlchemy models & Pydantic schemas
│   │       │   ├── models.py
│   │       │   └── schemas.py
│   │       ├── services/      # Business logic / orchestrators
│   │       │   ├── ingestion_service.py
│   │       │   ├── retrieval_service.py
│   │       │   ├── copilot_service.py
│   │       │   ├── llm_gateway.py
│   │       │   └── evaluation_service.py
│   │       ├── repositories/  # Data access layer
│   │       │   ├── document_repository.py
│   │       │   ├── conversation_repository.py
│   │       │   └── feedback_repository.py
│   │       ├── utils/         # Low‑level helpers (parsing, chunking, embeddings)
│   │       │   ├── chunking.py
│   │       │   ├── parsing.py
│   │       │   └── embeddings.py
│   │       ├── prompts/       # Prompt templates for the LLM
│   │       │   └── answer_with_citations.txt
│   │       ├── tests/         # Unit tests (empty for now)
│   │       ├── requirements.txt
│   │       └── Dockerfile
│   └── web/                   # Next.js frontend (minimal scaffolding)
│       ├── app/
│       │   ├── page.tsx       # Chat page
│       │   ├── upload/
│       │   │   └── page.tsx   # File upload page
│       │   └── history/
│       │       └── page.tsx   # Conversation history page
│       ├── components/        # Shared React components
│       │   ├── ChatPanel.tsx
│       │   ├── UploadPanel.tsx
│       │   ├── SourcePanel.tsx
│       │   └── FeedbackButtons.tsx
│       ├── lib/
│       │   └── api.ts         # Helper for API calls
│       ├── package.json
│       ├── tsconfig.json
│       ├── next.config.js
│       ├── Dockerfile
│       └── README.md          # Frontend specific docs
├── infra/
│   └── docker-compose.yml     # Multi‑service development stack
├── docs/
│   ├── architecture.md        # High level architecture description
│   └── decisions/             # Architectural decision records
│       └── 0001-modular-monolith.md
├── data/
│   ├── uploads/               # User uploaded files (volume mount for dev)
│   └── samples/               # Sample documents for demos
├── .env.example               # Example environment variables
├── .gitignore
└── LICENSE
```

## Getting started

1. **Clone the repository**

   ```bash
   git clone <this-repo-url>
   cd archpilot-ai
   ```

2. **Create a `.env` file**

   Copy `.env.example` to `.env` and fill in your configuration (e.g. database URL, API keys).

3. **Start the stack**

   Use Docker Compose to launch Postgres, the API and web apps:

   ```bash
   docker compose -f infra/docker-compose.yml up --build
   ```

   The API will be available at [http://localhost:8000](http://localhost:8000) and the web UI at [http://localhost:3000](http://localhost:3000).

## Contributing

This project is intended as a reference implementation and learning exercise. Feel free to extend or adapt it to your own needs.  Contributions and suggestions are welcome!
