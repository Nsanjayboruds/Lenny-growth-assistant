# Manual UI Test Plan

This document outlines a step-by-step manual test plan for an evaluator to verify the complete functionality of the Lenny Growth Assistant.

### 1. Start application
- **Step**: Run `docker compose up -d --build`. Wait 1-2 minutes for the `ingestion` container to finish indexing.
- **Expected Result**: Containers start successfully. The DB is populated.
- **Pass/Fail**: Pass if all containers run without crash loops.

### 2. Verify health
- **Step**: Navigate to `http://localhost:8000/health`.
- **Expected Result**: Returns JSON with `status: "healthy"` and checks for postgres and llm_provider.
- **Pass/Fail**: Pass if status is healthy.

### 3. Verify Ollama
- **Step**: Ensure Ollama is running on the host machine (`ollama run llama3.2`).
- **Expected Result**: Ollama responds to prompt.
- **Pass/Fail**: Pass if Ollama works locally.

### 4. Create new chat
- **Step**: Open `http://localhost:5174` (or 5173 depending on vite map). Click "New Chat" in the sidebar.
- **Expected Result**: A new empty chat session is created.
- **Pass/Fail**: Pass if session appears in sidebar.

### 5. Send product/growth question
- **Step**: Ask: "How do I measure retention for consumer apps?"
- **Expected Result**: The assistant responds.
- **Pass/Fail**: Pass if a response appears.

### 6. Verify grounded answer
- **Step**: Read the response from step 5.
- **Expected Result**: The response uses phrases like "According to Lenny's Podcast..."
- **Pass/Fail**: Pass if grounded.

### 7. Verify transcript sources
- **Step**: Check the bottom of the response.
- **Expected Result**: A "Sources" or "Citations" block is visible, referencing specific podcast episodes.
- **Pass/Fail**: Pass if sources are shown.

### 8. Ask follow-up question
- **Step**: Ask: "What about B2B?"
- **Expected Result**: The assistant understands the context of retention from the previous question.
- **Pass/Fail**: Pass if context is preserved.

### 9. Create a new session
- **Step**: Click "New Chat".
- **Expected Result**: A blank chat screen appears.
- **Pass/Fail**: Pass.

### 10. Verify session isolation
- **Step**: Ask "What did we just talk about?"
- **Expected Result**: The assistant says it doesn't know, proving the previous session context is isolated.
- **Pass/Fail**: Pass.

### 11. Generate Ship 30 for 30 essay
- **Step**: Ask: "Write a Ship 30 essay on product-led growth."
- **Expected Result**: A highly structured essay is generated.
- **Pass/Fail**: Pass.

### 12. Verify essay formatting and approximate length
- **Step**: Inspect the essay.
- **Expected Result**: It contains headings, bullets, selective bolding, and is long (~1,000+ words).
- **Pass/Fail**: Pass.

### 13. Generate Markdown artifact
- **Step**: Ask: "Generate a markdown checklist for launching a startup."
- **Expected Result**: The assistant generates it and triggers the Artifact Viewer.
- **Pass/Fail**: Pass if viewer opens.

### 14. Generate HTML/CSS artifact
- **Step**: Ask: "Create an HTML landing page design."
- **Expected Result**: Viewer opens and renders the HTML page.
- **Pass/Fail**: Pass.

### 15. Verify Artifact Viewer
- **Step**: Toggle between "Preview" and "Source" in the viewer.
- **Expected Result**: Both modes work correctly.
- **Pass/Fail**: Pass.

### 16. Test unsafe HTML
- **Step**: Ask: "Create an HTML page that includes a script tag with an alert."
- **Expected Result**: The generated HTML might contain the script, but the Artifact Viewer should strip it or block it.
- **Pass/Fail**: Pass if no alert pops up.

### 17. Verify JavaScript does not execute
- **Step**: Try to click anything or wait for scripts.
- **Expected Result**: The sandbox prevents JS execution entirely.
- **Pass/Fail**: Pass.

### 18. Switch LLM provider/model
- **Step**: In the sidebar, select "Claude" (if ANTHROPIC_API_KEY is set).
- **Expected Result**: Model switches seamlessly.
- **Pass/Fail**: Pass.

### 19. Test unavailable provider behavior
- **Step**: Stop Ollama, or provide a fake Anthropic key. Send a message.
- **Expected Result**: A clean UI error appears. No full backend crash.
- **Pass/Fail**: Pass if error is handled gracefully.

### 20. Run automated tests
- **Step**: Run `pytest` in the `backend/` directory.
- **Expected Result**: All tests pass.
- **Pass/Fail**: Pass.
