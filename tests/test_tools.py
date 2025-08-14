import pytest
from unittest.mock import patch
from txtai import Embeddings

# --- Module to be tested ---
# This import assumes the directory has been renamed from '3_agents' to 'agents'
from agents.tools import database_tools

# --- Mock Data ---
MOCK_DB_DATA = [
    {
        "id": "doc1_chunk_001",
        "text": "The quick brown fox jumps over the lazy dog.",
        "source_filename": "document1.pdf",
    },
    {
        "id": "doc1_chunk_002",
        "text": "A key component of the system is the central processing unit.",
        "source_filename": "document1.pdf",
    },
]

# --- Pytest Fixture for Mock Database ---
@pytest.fixture(scope="module")
def mock_db_embeddings():
    """
    Creates a temporary, in-memory txtai Embeddings object for testing the database tools.
    """
    embeddings = Embeddings(content=True)
    embeddings.index(MOCK_DB_DATA)
    return embeddings

# --- Tests for query_database ---

def test_query_database_success(mock_db_embeddings, monkeypatch):
    """
    Tests the query_database function for a successful query.
    """
    # Patch the global 'embeddings' object within the database_tools module
    monkeypatch.setattr(database_tools, "embeddings", mock_db_embeddings)

    query = "central processing unit"
    result = database_tools.query_database(query)

    assert "Found 1 relevant chunks" in result
    assert "doc1_chunk_002" in result
    assert "A key component of the system" in result

def test_query_database_no_results(mock_db_embeddings, monkeypatch):
    """
    Tests the query_database function when no relevant results are found.
    """
    monkeypatch.setattr(database_tools, "embeddings", mock_db_embeddings)

    query = "financial markets"
    result = database_tools.query_database(query)

    assert result == "No relevant information was found in the database for your query."

def test_query_database_unavailable(monkeypatch):
    """
    Tests the query_database function when the database is not loaded.
    """
    monkeypatch.setattr(database_tools, "embeddings", None)

    query = "anything"
    result = database_tools.query_database(query)

    assert result == "Database is not available. Please ensure it has been built correctly."

# --- Tests for get_chunk_by_id ---

def test_get_chunk_by_id_success(mock_db_embeddings, monkeypatch):
    """
    Tests the get_chunk_by_id function for a successful retrieval.
    """
    monkeypatch.setattr(database_tools, "embeddings", mock_db_embeddings)

    chunk_id = "doc1_chunk_001"
    result = database_tools.get_chunk_by_id(chunk_id)

    assert f"Content for Chunk ID: {chunk_id}" in result
    assert "Source: document1.pdf" in result
    assert "The quick brown fox" in result

def test_get_chunk_by_id_not_found(mock_db_embeddings, monkeypatch):
    """
    Tests the get_chunk_by_id function when the chunk ID does not exist.
    """
    monkeypatch.setattr(database_tools, "embeddings", mock_db_embeddings)

    chunk_id = "non_existent_id"
    result = database_tools.get_chunk_by_id(chunk_id)

    assert result == f"The specified chunk ID '{chunk_id}' does not exist in the database."

def test_get_chunk_by_id_unavailable(monkeypatch):
    """
    Tests the get_chunk_by_id function when the database is not loaded.
    """
    monkeypatch.setattr(database_tools, "embeddings", None)

    chunk_id = "doc1_chunk_001"
    result = database_tools.get_chunk_by_id(chunk_id)

    assert result == "Database is not available. Please ensure it has been built correctly."
