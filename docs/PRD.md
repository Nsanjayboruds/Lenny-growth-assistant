# Product Requirements Document (PRD)

## 1. Product Vision
Lenny Growth Assistant is an AI-powered conversational agent that provides growth, product management, and career advice deeply grounded in the wealth of knowledge from Lenny's Podcast. The assistant leverages Retrieval-Augmented Generation (RAG) to ensure that its answers are accurate and cited from actual transcript data. 

In addition to conversational QA, it provides specific skills like formatting answers into HTML/Markdown artifacts and creating structured writing formats (e.g., Ship 30 for 30 essays).

## 2. Target Audience
- Product Managers (Junior to Executive)
- Growth Marketers
- Startup Founders
- Professionals looking for career advice or insights from industry experts.

## 3. Core Capabilities & Use Cases

### 3.1. Knowledge Retrieval & Q&A
- **Use Case**: A user asks, "How do I measure retention for a B2B SaaS?"
- **Requirement**: The system retrieves the most relevant podcast transcripts, synthesizes a concise answer, and cites the sources directly.

### 3.2. Skill: Ship 30 for 30 Essay Generation
- **Use Case**: A user asks, "Write a Ship 30 essay on product-led growth."
- **Requirement**: The system applies a specialized skill prompt that formats the RAG-grounded insights into a highly engaging, structured short essay suitable for platforms like Twitter or LinkedIn.

### 3.3. Skill: Artifact Generation
- **Use Case**: A user asks, "Create an HTML landing page checklist based on Lenny's advice."
- **Requirement**: The system generates a clean, usable HTML or Markdown document and presents it in a dedicated "Artifact Viewer" panel alongside the chat, allowing the user to copy or render the artifact safely.

## 4. Technical Constraints & Non-Functional Requirements
- **Local vs Cloud LLM**: The application must support swapping between local models (Ollama) and cloud models (Anthropic) seamlessly.
- **Data Privacy & Security**: 
  - Sessions must be isolated.
  - HTML artifacts must be sanitized (using bleach/DOMPurify) to prevent XSS.
- **Resilience**: The backend must handle LLM API timeouts or misconfigurations gracefully with structured API error responses instead of failing silently.
- **Session Persistence**: Chat history must be saved in the database (PostgreSQL) so users can return to their previous conversations.

## 5. User Interface (UI) Requirements
- **Sidebar**: Manage chat sessions (New, Select, Delete). Toggle the active LLM provider (Ollama vs. Claude).
- **Chat Window**: Render Markdown-based AI responses, show loading states, and display errors inline.
- **Artifact Viewer**: A split-screen panel that conditionally appears when an artifact (HTML/Markdown) is generated, rendering it cleanly on the right side of the screen.

## 6. Success Metrics
- **Accuracy**: Answers should accurately reflect the source transcripts without hallucination.
- **Speed**: Local model inference should be reasonably fast, and cloud inference should be under 5 seconds.
- **User Engagement**: Users utilizing specific skills (Artifacts, Ship30) beyond basic chat.

---

# Forward Deployment Brief

## User and Problem
- **Primary User**: Startup Founders, Product Managers, and Growth Leads.
- **Job to be Done**: Rapidly query the extensive knowledge base of Lenny's Podcast to answer specific product and growth questions, without needing to listen to hundreds of hours of audio.
- **Pain Removed**: Replaces manual searching and note-taking with an instant, trustworthy RAG assistant that cites its sources, and auto-formats the findings into artifacts or Ship 30 essays.

## Success Metrics
- **Target Metric**: RAG Query Success Rate.
- **Measurement**: Measure the percentage of queries that return non-empty relevant sources (using pgvector similarity score) and successfully generate a grounded answer without triggering the fallback response.

## Assumptions
- The user will have a running Docker environment and sufficient system resources to run Ollama and PostgreSQL pgvector.
- The transcripts in the source repository are mostly complete and formatted in standard markdown.
- `claude-3-5-haiku` will be the default fallback for high-performance cloud processing, assuming the user sets the `ANTHROPIC_API_KEY`.

## Scope Choices
**IN SCOPE**:
- Fully functional local (Ollama) and cloud (Anthropic) inference toggling.
- Fully isolated chat sessions.
- Artifact viewer with HTML sanitization (Bleach).
- Automated transcript ingestion and pgvector chunking.

**OUT OF SCOPE**:
- User authentication and multi-tenant isolation. (Excluded to reduce scope complexity for a local/take-home assignment).
- Transcription generation. (We rely on existing text transcripts).

## Risks
- **Retrieval Quality**: Poorly phrased queries might miss relevant chunks, leading to fallback "Not enough evidence" responses.
- **Hallucination**: Even with grounding prompts, the LLM might infer beyond the transcripts.
- **Artifact Security**: User-generated HTML could execute malicious JS if the iframe sandbox or bleach sanitization fails.
- **Ingestion Failures**: If the github repository containing transcripts changes its structure, the ingestion script could break.

## Trade-offs
- **PostgreSQL/pgvector vs dedicated Vector DB (Pinecone/Milvus)**: Chose pgvector to keep the infrastructure simple and consolidated in one container, simplifying the evaluator setup.
- **Idempotent Ingestion on Startup**: Decided to run ingestion automatically in Docker compose to ensure the DB is populated, at the cost of a slightly longer initial boot. However, because it is idempotent, subsequent boots are near-instant.

## User Flows
1. **New chat → question → retrieval → grounded answer → sources**
2. **Conversation → Ship30 request → grounded essay**
3. **Conversation → artifact request → generation → Artifact Viewer**

## Acceptance Criteria
- [x] Evaluator can run `docker compose up -d` and the knowledge base automatically ingests the transcripts.
- [x] Evaluator can ask "What is product market fit?" and receive an answer citing at least one specific podcast episode.
- [x] Evaluator can request a Ship 30 essay, and the output is ~1,250 words with proper formatting and headings.
- [x] Evaluator can request an HTML artifact, and it renders securely in the Artifact Viewer.
- [x] All API calls return structured error JSON on failure, never exposing raw stack traces.
