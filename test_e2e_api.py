import httpx
import sys
import json

base_url = "http://localhost:8081/api"

try:
    # 1. Create session
    print("Creating session...")
    resp = httpx.post(f"{base_url}/sessions", json={"user_id": "test_user_123", "title": "Test Chat"})
    resp.raise_for_status()
    session_id = resp.json()["id"]
    print(f"Session created: {session_id}")

    # 2. Send message
    print("Sending message...")
    msg_data = {
        "content": "What does Brian Chesky say about design?",
        "provider": "ollama",
        "model": "llama3.2"
    }
    # stream=False
    with httpx.stream("POST", f"{base_url}/sessions/{session_id}/messages?stream=true", json=msg_data, timeout=30.0) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                parsed = json.loads(data)
                if "chunk" in parsed:
                    print(parsed["chunk"], end="", flush=True)
                elif "sources" in parsed:
                    print(f"\n\nSources: {len(parsed['sources'])} sources found.")
                elif "artifact" in parsed:
                    print(f"\n\nArtifact created: {parsed['artifact']['title']} ({parsed['artifact']['type']})")
    print("\n\nDone.")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
