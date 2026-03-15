# Agentic RAG API

A FastAPI backend that combines **Retrieval-Augmented Generation (RAG)** with an **agentic loop** powered by LangChain and an MCP (Model Context Protocol) tool server. Documents are chunked and stored in Pinecone; a GPT-4.1 agent dynamically selects the right namespace and search tool at query time.

---

## Architecture

```
Client
  │
  ▼
FastAPI  (port 8000)
  ├── POST /api/v1/upload          → Celery task → Pinecone upsert
  ├── DELETE /api/v1/delete-namespace
  ├── POST /api/v1/agent-response  → LangChain agent
  │                                      │
  │                                      ▼
  │                               MCP Server (port 9000)
  │                                 ├── retrive_all_name_spaces()
  │                                 ├── search_cars_vectors()
  │                                 └── search_addresses_vectors()
  │                                      │
  │                                      ▼
  │                                  Pinecone
  │
  ▼
Celery worker  ←→  Redis (broker + backend)
```

### Services (docker-compose)

| Container | Image | Port | Role |
|---|---|---|---|
| `agentic-rag-2` | custom | 8000 | FastAPI app |
| `mcp-server-rag-2` | custom | 9000 | FastMCP tool server |
| `celery-rag-2` | custom | — | Async document ingestion |
| `redis-rag-2` | redis:7-alpine | 6379 | Celery broker & result backend |
| `agentic-postgres-2` | postgres:17-alpine | 5432 | Relational store |

---

## API Endpoints

### `POST /api/v1/upload`
Upload a text document and assign it to a category. Processing is handled asynchronously by a Celery worker which chunks the document and upserts it into Pinecone.

**Form params**
- `user_file` — text file to upload
- `category` — `cars` | `addresses`

**Response**
```json
{ "success": "data uploaded" }
```

---

### `DELETE /api/v1/delete-namespace`
Remove a namespace (category) and all its vectors from the Pinecone index.

**Query params**
- `category` — namespace name to delete

**Response**
```json
{ "response": "Namespace cars successfully removed." }
```

---

### `POST /api/v1/agent-response`
Ask the agent a question. It will:
1. Call `retrive_all_name_spaces()` to discover available namespaces.
2. Route to `search_cars_vectors` or `search_addresses_vectors` based on the question topic.
3. Return a concise answer grounded in the vector database results.

**Query params**
- `question` — max 100 characters

**Response** — plain string answer from the agent.

---

## MCP Tools

The MCP server exposes three tools consumed by the LangChain agent via `langchain-mcp-adapters`:

| Tool | Description |
|---|---|
| `retrive_all_name_spaces()` | Lists all namespaces in the Pinecone index |
| `search_cars_vectors(question, name_space)` | Semantic search over car data (top-3 hits) |
| `search_addresses_vectors(question, name_space)` | Semantic search over address/people data (top-3 hits) |

---

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
ENVIRONMENT=development

# OpenAI
OPENAI_API_KEY=sk-...

# Pinecone
PINECONE_API_KEY=...
PINECONE_REGION=us-east-1
PINECONE_CLOUD=aws
INDEX_NAME=your-index-name

# Redis (overridden in docker-compose for container networking)
REDIS_HOST=localhost
REDIS_PORT=6379

# Postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ragdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# AWS (production only)
# AWS_SECRET_NAME=...
# AWS_REGION=...
```

> In **production**, set `ENVIRONMENT=production`. Secrets are then pulled from AWS Secrets Manager instead of the `.env` file.

---

## Running with Docker

```bash
docker compose up --build -d
```

To stop:
```bash
docker compose down
```

To tail logs:
```bash
docker compose logs -f
```

---

## Running locally (development)

```bash
# Install dependencies
uv sync

# Start the MCP server
uv run fastmcp run ./app/mcp_server.py:mcp --transport http --port 9000

# In a separate terminal, start the FastAPI app
uv run uvicorn app.main:app --reload --port 8000

# In a separate terminal, start the Celery worker
uv run celery -A app.celery_tasks worker --loglevel=INFO
```

Interactive API docs available at: http://localhost:8000/docs

---

## Document Ingestion

Documents are split on the separator `- - - - - - - - - -` into chunks of up to 200 characters. Each chunk is upserted as a record into Pinecone using the `llama-text-embed-v2` embedding model with cosine similarity. If the index does not exist it is created automatically on first upload.

---

## Content Filtering

The agent middleware (`ContentFilterMiddleware`) blocks requests containing prohibited keywords (e.g. `hack`, `exploit`, `malware`, `bomb`, `remote code execution`) before any model call is made, returning a safe refusal message.
