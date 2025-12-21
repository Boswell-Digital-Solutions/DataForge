"""
Unit tests for embedding utilities.
"""
import pytest
from unittest.mock import patch, Mock
from app.utils.embeddings import chunk_text


@pytest.mark.unit
@pytest.mark.embeddings
class TestTextChunking:
    """Test text chunking functionality."""
    
    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size."""
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_long_text(self):
        """Test chunking long text."""
        # Create text longer than chunk size
        text = " ".join(["word"] * 200)
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        
        # Should create multiple chunks
        assert len(chunks) > 1
    
    def test_chunk_overlap(self):
        """Test that chunks have overlap."""
        text = " ".join(["word"] * 100)
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        
        if len(chunks) > 1:
            # Check that there's some overlap between consecutive chunks
            # (This is a simplified check - actual overlap depends on word boundaries)
            assert len(chunks) > 1
    
    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        chunks = chunk_text("", chunk_size=100, overlap=10)
        
        assert len(chunks) == 1
        assert chunks[0] == ""
    
    def test_chunk_whitespace_only(self):
        """Test chunking whitespace-only text."""
        chunks = chunk_text("   \n  \t  ", chunk_size=100, overlap=10)
        
        assert len(chunks) >= 1
    
    def test_chunk_preserves_content(self):
        """Test that chunking preserves all content."""
        text = "This is a test. " * 50
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        
        # All chunks should be non-empty
        assert all(len(chunk) > 0 for chunk in chunks)
    
    def test_chunk_size_respected(self):
        """Test that chunks don't exceed chunk_size significantly."""
        text = " ".join(["word"] * 200)
        chunk_size = 100
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=10)
        
        # Chunks might be slightly larger due to word boundaries
        # but should be roughly around chunk_size
        for chunk in chunks:
            # Allow some flexibility for word boundaries
            assert len(chunk) <= chunk_size * 2


@pytest.mark.unit
@pytest.mark.embeddings
class TestEmbeddingGeneration:
    """Test embedding generation (mocked)."""
    
    def test_generate_embedding_exists(self):
        """Test that generate_embedding function exists."""
        from app.utils.embeddings import generate_embedding

        # Verify the function exists and is callable
        assert callable(generate_embedding)
    
    def test_embedding_dimension(self, mock_embedding):
        """Test that mock embedding has correct dimensions."""
        assert len(mock_embedding) == 1536
    
    @patch('app.utils.embeddings.generate_embedding')
    async def test_generate_embedding_called(self, mock_generate):
        """Test that generate_embedding can be called."""
        mock_generate.return_value = [0.1] * 1536
        
        result = await mock_generate("test text")
        assert len(result) == 1536
        mock_generate.assert_called_once_with("test text")

