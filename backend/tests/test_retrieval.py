"""
Tests for Retrieval Service logic.
We mock the database to test the query building and metadata preservation
without requiring a live pgvector database during unit testing.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.retrieval import RetrievalService
from app.schemas.schemas import SourceCitation

@pytest.mark.asyncio
async def test_retrieval_returns_relevant_chunks():
    """Test that relevant query returns chunk citations properly."""
    mock_db = AsyncMock()
    
    with patch("app.providers.ollama.OllamaProvider.embed", return_value=[0.1, 0.2, 0.3]):
        service = RetrievalService(mock_db)
        
        # Mock database result
        mock_result = MagicMock()
        
        # Simulate row returned from pgvector query
        # Columns: id, text, episode_title, guest, youtube_url, similarity
        mock_row = MagicMock()
        mock_row.text = "Product market fit is essential."
        mock_row.episode_title = "Lenny Episode 1"
        mock_row.guest = "Lenny"
        mock_row.youtube_url = "http://youtube.com/1"
        mock_row.score = 0.8
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result
        
        citations = await service.retrieve("What is PMF?")
        
        assert len(citations) == 1
        assert citations[0].chunk_text == "Product market fit is essential."
        assert citations[0].episode_title == "Lenny Episode 1"
        assert citations[0].guest == "Lenny"
        assert citations[0].score == 0.8

@pytest.mark.asyncio
async def test_empty_retrieval_handling():
    """Test empty retrieval behaves safely."""
    mock_db = AsyncMock()
    
    with patch("app.providers.ollama.OllamaProvider.embed", return_value=[0.1, 0.2, 0.3]):
        service = RetrievalService(mock_db)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result
        
        citations = await service.retrieve("Irrelevant query about aliens")
        
        assert len(citations) == 0
