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

   From Windows with Docker Engine installed inside WSL Ubuntu, run:

   ```powershell
   wsl.exe -d Ubuntu -- bash -lc "cd /mnt/c/Users/bruno/github/archpilot-ai && docker compose -f infra/docker-compose.yml up --build"
   ```

## Database migrations

The API uses Alembic for schema management. The API container runs `alembic upgrade head` before starting FastAPI, so a clean Docker Compose database is initialized automatically.

Run migrations manually:

```bash
docker compose -f infra/docker-compose.yml run --rm api alembic upgrade head
```

Rollback the latest migration in a local/dev database. The baseline rollback removes the initial schema tables, so do not run it against data you need to keep:

```bash
docker compose -f infra/docker-compose.yml run --rm api alembic downgrade -1
```

Reset the local database volume and rebuild:

```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up --build
```

From Windows using Docker Engine inside WSL Ubuntu:

```powershell
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/c/Users/bruno/github/archpilot-ai && docker compose -f infra/docker-compose.yml run --rm api alembic upgrade head"
```

The baseline migration enables the PostgreSQL `vector` extension and creates an HNSW cosine index on `document_chunks.embedding`. HNSW was chosen over IVFFlat because it works well for incremental inserts without a separate training step; the trade-off is higher memory usage and index build cost.

## Chat features

- `/chat/query` returns the existing JSON answer response for compatibility.
- `/chat/query/stream` streams answer deltas as server-sent events for the web chat UI.
- `/chat/conversations` and `/chat/conversations/{id}` expose persisted conversation history.
- `/chat/messages/{message_id}/diagnostics` returns persisted retrieval diagnostics for an assistant answer.
- The web UI renders basic markdown in answers and turns cited chunk IDs into numbered citation cards.
- Retrieval uses pgvector when query embeddings are available, blends vector and keyword candidates, reranks the combined set, and supports `project_id`, `document_filename`, and `content_type` filters on chat requests.
- Chat responses include retrieval diagnostics: retrieval mode, applied filters, source content type, project name, source signal (`vector`, `keyword`, `hybrid`, or `latest`), retrieval latency, and provider/model metadata.

## Evaluation

ArchPilot includes a local evaluation pipeline for checking retrieval and answer quality without sending data to an external judge model. The first implementation stores datasets, cases, runs, and per-case results in Postgres, then computes deterministic metrics:

- context precision and recall when expected chunk IDs are provided
- citation coverage based on cited retrieved chunk IDs
- answer completeness based on expected facts
- retrieval latency

Evaluation APIs:

- `POST /evaluations/datasets`
- `GET /evaluations/datasets`
- `POST /evaluations/datasets/{dataset_id}/cases`
- `GET /evaluations/datasets/{dataset_id}/cases`
- `POST /evaluations/runs`
- `GET /evaluations/runs`
- `GET /evaluations/runs/{run_id}`

The web UI exposes these workflows at [http://localhost:3000/evaluations](http://localhost:3000/evaluations). A small starter dataset is available at `data/samples/evaluation_dataset.json`.

## Demo data and public reference materials

The repository includes a small local demo material set in `data/samples/demo-materials`. It contains an ArchPilot MVP reference note and a public-reference catalog with links to architecture sources. Load it into the running database with:

```bash
docker compose -f infra/docker-compose.yml run --rm api python -m app.scripts.seed_demo_data
```

From Windows using Docker Engine inside WSL Ubuntu:

```powershell
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/c/Users/bruno/github/archpilot-ai && docker compose -f infra/docker-compose.yml run --rm api python -m app.scripts.seed_demo_data"
```

The command creates or reuses an `ArchPilot Demo Reference` project and skips files that were already loaded for that project.

To load your own public reference materials:

1. Download allowed `.txt`, `.md`, `.json`, or `.pdf` files into `data/samples/demo-materials` or another folder under `data/samples`.
2. Run the seed command again, optionally with a custom folder and project name:

   ```bash
   docker compose -f infra/docker-compose.yml run --rm api python -m app.scripts.seed_demo_data --materials-dir data/samples/demo-materials --project-name "Public Architecture References"
   ```

Useful public starting points:

- [C4 model](https://c4model.com/) for software architecture diagrams and abstractions.
- [arc42 downloads](https://arc42.org/download) for architecture documentation templates.
- [Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework) for workload quality guidance.
- [NIST SP 800-160 Vol. 1 Rev. 1](https://csrc.nist.gov/pubs/sp/800/160/v1/r1/final) for systems security engineering guidance.

Only download and ingest public materials when their license or terms allow your intended use. Do not put proprietary documents, secrets, or API keys in `data/samples`.

## Observability

The API emits structured JSON logs with a request ID, method, path, status code, and duration. Incoming `X-Request-ID` headers are preserved; otherwise the API generates one and returns it as `x-request-id`.

Local metrics are available in Prometheus text format:

```bash
curl http://localhost:8000/metrics/
```

Current local metrics include HTTP request/error counts, HTTP latency, uploaded documents, chat requests, retrieval latency, LLM duration, streaming time to first token, and evaluation run/case counts.

To run the optional local metrics stack:

```bash
docker compose -f infra/docker-compose.yml --profile observability up --build
```

Prometheus is available at [http://localhost:9090](http://localhost:9090), and Grafana is available at [http://localhost:3001](http://localhost:3001). The default local Grafana credentials are `admin` / `admin`, unless `GRAFANA_ADMIN_USER` or `GRAFANA_ADMIN_PASSWORD` are set.

## Contributing

This project is intended as a reference implementation and learning exercise. Feel free to extend or adapt it to your own needs.  Contributions and suggestions are welcome!
