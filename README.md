# Lenny Growth Assistant

> An AI assistant grounded in 269 Lenny's Podcast transcripts. Ask product management and growth questions, get answers with source citations, and generate Ship 30 essays or HTML/Markdown artifacts.

---

## Features

| Feature | Description |
|---|---|
| 💬 Grounded Chat | RAG-powered Q&A with source citations from Lenny's Podcast |
| 📚 Source Citations | Every answer links back to specific episodes with relevance scores |
| ✍️ Ship 30 Essays | Generate 1,250-word essays following Ship 30 for 30 principles |
| 🎨 Artifact Generation | Create Markdown docs or HTML pages from conversation context |
| 🔒 Sandboxed Viewer | HTML artifacts rendered in a sandboxed iframe (scripts disabled) |
| ⚡ Local Inference | Runs fully offline with Ollama (llama3.2) |
| ☁️ Cloud Option | Switch to Anthropic Claude with one env var change |
| 🔄 Session Memory | Full conversation history per session |

---

## Quick Start

### Prerequisites

- Docker + Docker Compose v2
- Ollama installed and running (`ollama serve`)
- Git

### 1. Clone and Configure

```bash
git clone <this-repo>
cd lenny-growth-assistant
cp .env.example .env
# Edit .env if needed (defaults work for Ollama)
```

### 2. Pull Required Ollama Models

```bash
# Chat model (2 GB)
ollama pull llama3.2

# Embedding model (274 MB)
ollama pull nomic-embed-text
```

### 3. Start Services

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** with pgvector at `localhost:5432`
- **Backend API** at `http://localhost:8000`
- **Frontend** at `http://localhost:5173`
- **Migration runner** (runs once, then exits)

### 4. Wait for Knowledge Base Ingestion (Automatic)

When you run `docker compose up`, an `ingestion` container automatically starts. 
- It clones the transcript repository and uses Ollama to embed the chunks into PostgreSQL. 
- This process is **idempotent**: it will take 10-40 minutes on the very first run, but will be near-instant on subsequent restarts.
- **You MUST wait** for this to finish before asking questions, or you will get a "Not enough evidence" response.

*(Optional)* If you want to run it manually without docker:
```bash
cd backend
pip install -r requirements.txt
python -m ingestion.index
```

### 5. Open the App

Navigate to **http://localhost:5173**

---

## Using the App

### Chat
Ask any product management or growth question:
- *"What does Lenny say about product-market fit?"*
- *"How do top PMs approach prioritization?"*
- *"What retention metrics matter most for consumer apps?"*

### Ship 30 Essay
Ask for an essay:
- *"Write a Ship 30 essay about growth loops"*
- *"Write an essay about this conversation"*

### Artifact Generation
Generate formatted documents:
- *"Create an HTML landing page for a PMF framework"*
- *"Generate a Markdown report on retention strategies"*

### Switch Models
Use the **Model** selector in the sidebar to toggle between:
- **Ollama** (local, private, free)
- **Anthropic Claude** (cloud, requires `ANTHROPIC_API_KEY` in `.env`)

---

## Configuration

All configuration lives in `.env`:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` or `anthropic` |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama URL |
| `OLLAMA_MODEL` | `llama3.2` | Chat model |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `ANTHROPIC_API_KEY` | *(empty)* | Required for Anthropic |
| `ANTHROPIC_MODEL` | `claude-3-5-haiku-20241022` | Claude model |
| `RETRIEVAL_TOP_K` | `8` | Chunks to retrieve per query |
| `RETRIEVAL_SCORE_THRESHOLD` | `0.5` | Minimum similarity score |

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt

# Run all tests (requires running PostgreSQL)
pytest

# Run only security tests (no DB needed)
pytest tests/test_security.py tests/test_routing_and_chunks.py -v
```

---

## Project Structure

```
lenny-growth-assistant/
├── frontend/          # React + Vite + TypeScript + Tailwind
├── backend/
│   ├── app/
│   │   ├── api/       # FastAPI routers (health, sessions, messages, artifacts)
│   │   ├── agents/    # CHAT, SHIP30, ARTIFACT skills + router
│   │   ├── providers/ # Ollama + Anthropic provider abstraction
│   │   ├── services/  # retrieval.py, sanitizer.py
│   │   ├── models/    # SQLAlchemy ORM models
│   │   └── schemas/   # Pydantic request/response schemas
│   ├── tests/         # pytest test suite
│   └── alembic/       # Database migrations
├── ingestion/         # Transcript download, parse, chunk, embed, index
├── skills/ship30/     # Ship 30 principles, template, SKILL.md
└── docs/              # PRD, design doc, architecture doc
```

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | System health check |
| `POST` | `/api/sessions` | Create session |
| `GET` | `/api/sessions` | List sessions |
| `GET` | `/api/sessions/{id}` | Get session |
| `PATCH` | `/api/sessions/{id}` | Update session title |
| `DELETE` | `/api/sessions/{id}` | Delete session |
| `POST` | `/api/sessions/{id}/messages` | Send message (triggers agent) |
| `GET` | `/api/sessions/{id}/messages` | List messages |
| `GET` | `/api/artifacts/{id}` | Get artifact |
| `GET` | `/api/artifacts/session/{id}` | List session artifacts |

Full interactive docs: `http://localhost:8000/docs`

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for system diagrams.

---

## Known Limitations

- First ingestion takes 10–40 minutes (269 episodes × ~30 chunks × embedding time)
- HTML artifacts are sanitized server-side and rendered in a sandboxed iframe (no JS)
- No authentication — sessions use client-side IDs (by design, per scope)
- Ollama inference is slower than cloud APIs on low-RAM machines

---

## License

MIT
