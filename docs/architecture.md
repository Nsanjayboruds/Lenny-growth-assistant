# Architecture: Lenny Growth Assistant

## System Overview

```mermaid
graph TB
    User((User)) --> FE[Frontend<br/>React + Vite + Tailwind<br/>:5173]
    FE --> |REST API| API[FastAPI Backend<br/>:8000]
    API --> |async queries| DB[(PostgreSQL<br/>+ pgvector<br/>:5432)]
    API --> |HTTP| Ollama[Ollama<br/>:11434<br/>llama3.2]
    API --> |HTTPS| Anthropic[Anthropic API<br/>Claude]

    style FE fill:#6c63ff,color:#fff
    style API fill:#4839bf,color:#fff
    style DB fill:#22223b,color:#fff
    style Ollama fill:#2d5a27,color:#fff
    style Anthropic fill:#8b4513,color:#fff
```

## Request Flow — Chat Query

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant R as Router
    participant RAG as RAG Service
    participant PG as pgvector
    participant LLM as LLM Provider

    U->>FE: Types message
    FE->>API: POST /api/sessions/{id}/messages
    API->>R: route_intent(message)
    R-->>API: Intent.CHAT
    API->>RAG: retrieve(query)
    RAG->>PG: embed query → cosine search
    PG-->>RAG: top-8 chunks
    RAG-->>API: citations[]
    API->>LLM: generate(context + history)
    LLM-->>API: grounded response
    API->>PG: persist user + assistant messages
    API-->>FE: MessageResponse + sources
    FE->>U: Renders answer + citations
```

## Agent Routing

```mermaid
graph LR
    MSG[User Message] --> KEYWORD{Keyword<br/>Match?}
    KEYWORD -->|ship30, essay, newsletter| SHIP30[Ship30 Agent]
    KEYWORD -->|html, landing page, artifact| ARTIFACT[Artifact Agent]
    KEYWORD -->|no match| LLM{LLM<br/>Classifier}
    LLM -->|SHIP30| SHIP30
    LLM -->|ARTIFACT| ARTIFACT
    LLM -->|CHAT| CHAT[Chat Agent]
    LLM -->|error| CHAT

    SHIP30 --> RAG[RAG Retrieval]
    ARTIFACT --> RAG
    CHAT --> RAG

    RAG --> PROVIDER[LLM Provider<br/>Ollama / Anthropic]
```

## Database Schema

```mermaid
erDiagram
    sessions ||--o{ messages : has
    sessions ||--o{ artifacts : has
    transcripts ||--o{ transcript_chunks : has

    sessions {
        uuid id PK
        string title
        datetime created_at
        datetime updated_at
    }

    messages {
        uuid id PK
        uuid session_id FK
        string role
        text content
        text sources
        string intent
        datetime created_at
    }

    artifacts {
        uuid id PK
        uuid session_id FK
        string artifact_type
        string title
        text content
        text sanitized_content
        datetime created_at
    }

    transcripts {
        uuid id PK
        string slug
        string guest
        text title
        text youtube_url
        datetime created_at
    }

    transcript_chunks {
        uuid id PK
        uuid transcript_id FK
        int chunk_index
        text text
        string text_hash
        vector embedding
        string guest
        text episode_title
        datetime created_at
    }
```

## LLM Provider Abstraction

```mermaid
classDiagram
    class LLMProvider {
        <<abstract>>
        +generate(messages, max_tokens, temperature, system) LLMResponse
        +health_check() dict
        +provider_name() str
        +model_name() str
    }

    class OllamaProvider {
        -base_url: str
        -model: str
        -embedding_model: str
        +generate()
        +embed(text) list[float]
        +health_check()
    }

    class AnthropicProvider {
        -client: AsyncAnthropic
        -model: str
        +generate()
        +health_check()
    }

    class get_provider {
        <<factory>>
        +get_provider(override) LLMProvider
    }

    LLMProvider <|-- OllamaProvider
    LLMProvider <|-- AnthropicProvider
    get_provider --> OllamaProvider : creates
    get_provider --> AnthropicProvider : creates
```

## Ingestion Pipeline

```mermaid
graph LR
    GH[GitHub Repo<br/>ChatPRD/lennys-podcast-transcripts] --> DL[download.py<br/>git clone/pull]
    DL --> PARSE[parse.py<br/>YAML frontmatter + body]
    PARSE --> CHUNK[chunk.py<br/>Paragraph-aware<br/>~600 tokens, 100 overlap]
    CHUNK --> EMBED[embed.py<br/>nomic-embed-text<br/>768-dim vectors]
    EMBED --> INDEX[index.py<br/>PostgreSQL + pgvector<br/>HNSW index]

    style GH fill:#333,color:#fff
    style INDEX fill:#22223b,color:#fff
```

## Security Architecture

```mermaid
graph TB
    LLM["LLM Output<br/>HTML"] --> BLEACH["bleach sanitizer<br/>allowlist-based"]
    BLEACH --> CSS["Style tag cleaning<br/>remove expression(), @import"]
    CSS --> STORE["Store sanitized_content<br/>in PostgreSQL"]
    STORE --> IFRAME["sandboxed iframe<br/>sandbox=allow-same-origin<br/>No scripts, No forms<br/>No navigation"]

    style BLEACH fill:#8b4513,color:#fff
    style IFRAME fill:#2d5a27,color:#fff
```

## Key Design Decisions

### 1. Paragraph-Aware Chunking
Instead of fixed-character splitting, we split on paragraph boundaries and speaker turns. This preserves conversational context and produces semantically coherent chunks that retrieve better.

### 2. nomic-embed-text for Embeddings
- 768-dimension vectors (vs. 1536 for OpenAI text-embedding-3-small)
- Runs locally via Ollama — no external API dependency for embeddings
- High quality: trained on diverse text including conversational transcripts

### 3. HNSW Index
pgvector's HNSW (Hierarchical Navigable Small World) index provides O(log n) approximate nearest neighbor search. With m=16 and ef_construction=64, it balances recall quality with index build time.

### 4. Intent Router — Keyword + LLM Fallback
The keyword pre-check catches obvious cases (essay, ship30, html) without an LLM call. For ambiguous cases, a cheap 10-token LLM call classifies intent. This keeps routing fast and predictable.

### 5. Anti-Hallucination System Prompt
The chat agent's system prompt explicitly instructs the LLM to:
- Only cite what's in the retrieved context
- Use exact attribution format
- Respond with an insufficient-evidence message when context is absent
- Distinguish inference from retrieved evidence

### 6. HTML Sandbox Security Layers
HTML artifacts go through two security layers:
1. **Server-side**: `bleach` allowlist sanitizer strips scripts, event handlers, and dangerous protocols
2. **Client-side**: Sandboxed iframe with `sandbox="allow-same-origin"` — blocks JS execution even if sanitizer misses something

## Performance Characteristics

| Operation | Typical Time |
|---|---|
| Query embedding (nomic-embed-text) | 50–200ms |
| pgvector HNSW search (20k chunks) | <5ms |
| Ollama llama3.2 response (1500 tokens) | 10–60s (hardware dependent) |
| Anthropic claude-3-5-haiku response | 2–8s |
| Full request round-trip (Ollama) | 15–65s |
| Full request round-trip (Anthropic) | 3–10s |
