"""
Tests for the API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health endpoint should return 200 with status field."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "checks" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_includes_postgres_check(client: AsyncClient):
    """Health check should report postgres status."""
    response = await client.get("/health")
    data = response.json()
    assert "postgres" in data["checks"]


@pytest.mark.asyncio
async def test_health_includes_llm_check(client: AsyncClient):
    """Health check should report LLM provider status."""
    response = await client.get("/health")
    data = response.json()
    assert "llm_provider" in data["checks"]


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient):
    """Creating a session should return 201 with session data."""
    response = await client.post("/api/sessions", json={"title": "Test Chat", "user_id": "anon-user-123"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Chat"
    assert data["user_id"] == "anon-user-123"
    assert "id" in data
    assert "created_at" in data
    assert data["message_count"] == 0


@pytest.mark.asyncio
async def test_create_session_default_title(client: AsyncClient):
    """Session should have default title if not provided."""
    response = await client.post("/api/sessions", json={})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Chat"


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient):
    """Listing sessions should return a list."""
    # Create a session first
    await client.post("/api/sessions", json={"title": "List Test"})
    response = await client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total" in data
    assert isinstance(data["sessions"], list)


@pytest.mark.asyncio
async def test_get_session(client: AsyncClient):
    """Getting a session by ID should return 200 with session data."""
    create_resp = await client.post("/api/sessions", json={"title": "Get Test"})
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["title"] == "Get Test"


@pytest.mark.asyncio
async def test_get_nonexistent_session(client: AsyncClient):
    """Getting a nonexistent session should return 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/sessions/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient):
    """Deleting a session should return 204."""
    create_resp = await client.post("/api/sessions", json={"title": "Delete Test"})
    session_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/sessions/{session_id}")
    assert delete_resp.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_messages_empty_session(client: AsyncClient):
    """New session should have empty messages list."""
    create_resp = await client.post("/api/sessions", json={"title": "Empty"})
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/sessions/{session_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_messages_invalid_session(client: AsyncClient):
    """Getting messages for nonexistent session should return 404."""
    fake_id = "00000000-0000-0000-0000-000000000001"
    response = await client.get(f"/api/sessions/{fake_id}/messages")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_message_invalid_session(client: AsyncClient):
    """Sending a message to a nonexistent session should return 404."""
    fake_id = "00000000-0000-0000-0000-000000000002"
    response = await client.post(
        f"/api/sessions/{fake_id}/messages",
        json={"content": "Hello"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_message_empty_content(client: AsyncClient):
    """Sending an empty message should return 422."""
    create_resp = await client.post("/api/sessions", json={"title": "Validation Test"})
    session_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_session_isolation(client: AsyncClient):
    """Messages in one session should not appear in another."""
    # Create two sessions
    resp1 = await client.post("/api/sessions", json={"title": "Session A"})
    resp2 = await client.post("/api/sessions", json={"title": "Session B"})
    session_a = resp1.json()["id"]
    session_b = resp2.json()["id"]

    # Verify they have separate message lists
    msgs_a = await client.get(f"/api/sessions/{session_a}/messages")
    msgs_b = await client.get(f"/api/sessions/{session_b}/messages")

    assert msgs_a.json()["messages"] == []
    assert msgs_b.json()["messages"] == []
    assert session_a != session_b
