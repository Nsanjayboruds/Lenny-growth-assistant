# Design Document

## 1. System Overview
The Lenny Growth Assistant is built using a modern modular architecture to separate concerns and ensure maintainability. It consists of a React/Vite frontend and a FastAPI backend, communicating via REST. Data persistence and vector search are handled by PostgreSQL with the `pgvector` extension.

## 2. Architecture & Components

### 2.1. Frontend Architecture
- **Framework**: React 18, Vite, TypeScript.
- **Styling**: Tailwind CSS with a custom design system focusing on dark-mode glassmorphism and vibrant brand colors to ensure a premium look.
- **State Management**: React Context / Hooks (`useState`, `useEffect`) manage the session state and message history. 
- **Components**:
  - `App`: Core layout and state orchestrator.
  - `Sidebar`: Manages sessions and model selection.
  - `Chat`: Message rendering, auto-scrolling, and input handling.
  - `ArtifactViewer`: An isolated viewer for rendered HTML and Markdown artifacts, ensuring robust rendering and safe HTML display.

### 2.2. Backend Architecture
- **Framework**: FastAPI for asynchronous, high-performance API endpoints.
- **Database**: PostgreSQL with `pgvector` for storing embeddings and conversation history. `asyncpg` and SQLAlchemy are used for asynchronous database operations.
- **Agent Routing**: 
  - A lightweight intent router first uses keyword heuristics to route to `SHIP30` or `ARTIFACT`.
  - Falls back to an LLM-based classifier for ambiguous inputs to direct to the correct agent.
- **Skill Handlers**:
  - **Chat (RAG)**: Uses the similarity score of vector embeddings to pull in relevant podcast chunks and constructs a grounded prompt.
  - **Ship30**: Specifically instructs the LLM to format the response as a Ship 30 essay based on principles defined in `skills/ship30/`.
  - **Artifact**: Triggers code/markdown/HTML generation.

## 3. Data Model
- **Session**: Groups a collection of messages. 
- **Message**: Individual prompt or response, tracking `role` (user/assistant), `content`, and optionally `sources` or `intent`.
- **Artifact**: A specific piece of generated content (HTML or Markdown) linked to a message and session.

## 4. LLM Abstraction Layer
The application implements an `LLMProvider` interface to standardise calls across multiple providers.
- `OllamaProvider`: Interfaces with a local Ollama service for zero-cost, local inference (`llama3.2`).
- `AnthropicProvider`: Interfaces with the Anthropic API (`claude-3-5-haiku`) for cloud-based, high-quality responses.

## 5. Security & Isolation
- **Artifact Security**: User-generated HTML is sanitized using Python's `bleach` library in the backend before being sent to the frontend. The frontend uses `dangerouslySetInnerHTML` cautiously within a constrained container.
- **Error Handling**: API errors are caught globally in FastAPI to return structured JSON responses, preventing the leakage of internal stack traces.
