"""
pytest configuration and shared fixtures.
"""
import asyncio
import os
import pytest
import inspect
from httpx import AsyncClient, ASGITransport

original_getsourcelines = inspect.getsourcelines
def safe_getsourcelines(obj):
    try:
        return original_getsourcelines(obj)
    except OSError:
        return (["\n"], 0)
inspect.getsourcelines = safe_getsourcelines

from dotenv import load_dotenv

# Load .env from project root if it exists
dotenv_path = os.path.join(os.path.dirname(__file__), "../../.env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Set test environment before importing app
db_url = os.environ.get("DATABASE_URL", "")
if "@db:5432" in db_url:
    db_url = db_url.replace("@db:5432", "@localhost:5435")
elif not db_url:
    db_url = "postgresql+asyncpg://postgres:postgres@localhost:5435/lenny"

os.environ["DATABASE_URL"] = db_url
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("APP_ENV", "test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """HTTP client for testing the FastAPI app."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
