import httpx
import sys
import json

base_url = "http://localhost:8081/api"

try:
    print("Creating session...")
    resp = httpx.post(f"{base_url}/sessions", json={"user_id": "test_user_ship30", "title": "Ship 30 Test"})
    resp.raise_for_status()
    session_id = resp.json()["id"]
    print(f"Session created: {session_id}")

    print("Sending message...")
    msg_data = {
        "content": "Write an essay about product management using Ship 30 for 30 style.",
        "provider": "ollama",
        "model": "llama3.2"
    }
    with httpx.stream("POST", f"{base_url}/sessions/{session_id}/messages?stream=true", json=msg_data, timeout=600.0) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                parsed = json.loads(data)
                if "chunk" in parsed:
                    pass
                elif "artifact" in parsed:
                    print(f"\n\nArtifact created: {parsed['artifact']['title']} ({parsed['artifact']['type']})")
    print("\n\nDone.")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
